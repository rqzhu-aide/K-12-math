"""Rebuild and read the portable, reviewed mathematics graph using SQLite.

JSON/JSONL under knowledge-graph/source is authoritative, with optional installed
local mappings under knowledge-graph/local. SQLite is a derived runtime index,
opened read-only by readers. A requires edge points from the dependent to its
prerequisite. Route components remain optional alternatives.
"""
import argparse
from collections import deque
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from layout import database_root
import re
import sqlite3
import sys
import tempfile
import time

from question_banks import BankError, FIGURE, bank_root_for_question, figure_path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = '2'
DEFAULT_MAX_NODES = 16
DEFAULT_MAX_CHARS = 8000
RELATIONS = {'requires', 'prepares', 'method_component', 'related'}
STATUSES = {'accepted', 'rejected', 'unresolved'}
MAPPING_STATUSES = {'mapped', 'non_diagnostic', 'unresolved'}
NON_DIAGNOSTIC_MEANING = (
    'The displayed task supplies the answer relation. Contextual concepts are definitions only; '
    'the response does not establish mastery or a gap in them. Do not expand prerequisites or methods.'
)
HASH = re.compile(r'[0-9a-f]{64}')
MEANING = (
    'Mathematical graph context; each record states its review status. '
    'This is not evidence of learner mastery or a persistent gap. '
    'requires means the dependent needs the prerequisite within its stated scope; '
    'prepares is useful background. Routes are optional alternatives, not an AND group. '
    'Use the displayed task and observed student method; do not infer ancestors mastered '
    'or missing from a single answer. Machine review is not teacher validation.'
)
FINGERPRINT_FIELDS = (
    'ID', 'Bank', 'Question', 'Question Type', 'Choices', 'Choices Type',
    'Correct Answer', 'ResponseType', 'Answer Form', 'Unordered Answers',
    'Accepted Answers', 'Rejected Answers', 'GradingStatus', 'Language',
    'Grade', 'Level', 'CurriculumUnit',
)


class GraphError(ValueError):
    """Invalid graph source, binding, or derived database."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _object(value, where):
    if not isinstance(value, dict):
        raise GraphError(f'{where}: expected an object.')


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise GraphError(f'{where}: expected nonempty text.')


def _strings(value, where, *, ids=None):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise GraphError(f'{where}: expected a list of nonempty strings.')
    if len(value) != len(set(value)):
        raise GraphError(f'{where}: duplicate entries.')
    if ids is not None and set(value) - set(ids):
        raise GraphError(f'{where}: unknown node IDs {sorted(set(value) - set(ids))}.')


def _reviews(value, where):
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise GraphError(f'{where}: expected a list of review objects.')


def question_fingerprint(question, root=ROOT, *, bank_root=None):
    """Return {contentHash, figureHashes}, binding displayed content and answer rules.

    Only figures referenced in Question or Choices are hashed, using their bank
    relative figures/ paths as keys. Solution, metadata, graph tags and source
    labels are excluded. Missing/unsafe referenced images raise GraphError.
    bank_root is for validating an import before it is installed.
    """
    _object(question, 'question')
    from question_format_v3 import is_v3, normalize_question, fingerprint_payload, QuestionFormatError
    v3 = is_v3(question)
    try:
        question = normalize_question(question, root=root, bank_root=bank_root)
    except QuestionFormatError as exc:
        raise GraphError(str(exc)) from None
    if v3:
        payload = fingerprint_payload(question)
    else:
        payload = {key: question.get(key) for key in FINGERPRINT_FIELDS}
        for key in ('Accepted Answers', 'Rejected Answers'):
            payload[key] = question.get(key, [])
        payload['Unordered Answers'] = question.get('Unordered Answers', False)
    choices = question.get('Choices', {})
    if not isinstance(question.get('Question'), str) or not isinstance(choices, dict):
        raise GraphError('Question and Choices must contain displayed text.')
    if any(not isinstance(x, str) for x in choices.values()):
        raise GraphError('Choice values must be displayed text.')
    method_texts = [m['explanation'] for m in question.get('SolutionMethods', []) if m.get('explanation')] if v3 else []
    relative_figures = sorted({match.group(1) for text in [question['Question'], *choices.values(), *method_texts]
                               for match in FIGURE.finditer(text)})
    hashes = {}
    try:
        if relative_figures:
            bank = Path(bank_root).resolve() if bank_root is not None else bank_root_for_question(question, Path(root))
            for relative in relative_figures:
                hashes[relative] = hashlib.sha256(figure_path(bank, relative).read_bytes()).hexdigest()
    except (BankError, OSError, TypeError, ValueError) as exc:
        raise GraphError(f'Cannot bind question figures: {exc}') from None
    return {'contentHash': _digest({'question': payload, 'figureHashes': hashes}), 'figureHashes': hashes}


def load_question(question_id, root=ROOT):
    """Use the assessor's installed-bank ID/path checks without a model call."""
    from student_assessment import AssessmentError, StudentAssessment
    try:
        return StudentAssessment(config=object(), root=Path(root))._question(question_id)
    except (AssessmentError, BankError, OSError, ValueError) as exc:
        raise GraphError(f'{question_id}: cannot load installed question ({exc}).') from None


def validate_mapping(mapping, node_ids):
    """Validate one mapping and every route reference; never resolve arbitrary tags."""
    _object(mapping, 'mapping')
    qid = mapping.get('questionId', '(missing)')
    for field in ('questionId', 'bank', 'reviewStatus', 'rationale'):
        _text(mapping.get(field), f'{qid}.{field}')
    if mapping.get('status') not in MAPPING_STATUSES:
        raise GraphError(f'{qid}: mapping status must be mapped, non_diagnostic or unresolved.')
    if not isinstance(mapping.get('contentHash'), str) or not HASH.fullmatch(mapping['contentHash']):
        raise GraphError(f'{qid}: invalid contentHash.')
    for field in ('assessedIds', 'supportIds'):
        _strings(mapping.get(field), f'{qid}.{field}', ids=node_ids)
    if 'contextualIds' in mapping:
        _strings(mapping['contextualIds'], f'{qid}.contextualIds', ids=node_ids)
    if mapping['status'] == 'non_diagnostic':
        if not mapping.get('contextualIds'):
            raise GraphError(f'{qid}: a non_diagnostic question needs contextualIds.')
        if mapping['assessedIds'] or mapping['supportIds'] or mapping.get('routes'):
            raise GraphError(f'{qid}: non_diagnostic context cannot assert assessed, support or route knowledge.')
    _strings(mapping.get('flags'), f'{qid}.flags')
    _object(mapping.get('answerCheck'), f'{qid}.answerCheck')
    if 'headingContext' in mapping:
        _text(mapping['headingContext'], f'{qid}.headingContext')
    _object(mapping.get('figureHashes'), f'{qid}.figureHashes')
    for relative, digest in mapping['figureHashes'].items():
        if not isinstance(relative, str) or not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise GraphError(f'{qid}: invalid figure hash.')
    _reviews(mapping.get('reviews'), f'{qid}.reviews')
    routes = mapping.get('routes')
    if not isinstance(routes, list):
        raise GraphError(f'{qid}: routes must be a list.')
    seen = set()
    for route in routes:
        _object(route, f'{qid}.route')
        for field in ('id', 'label'):
            _text(route.get(field), f'{qid}.route.{field}')
        if route['id'] in seen:
            raise GraphError(f'{qid}: duplicate route ID {route["id"]}.')
        seen.add(route['id'])
        _strings(route.get('nodeIds'), f'{qid}.route.nodeIds', ids=node_ids)
        if not route['nodeIds']:
            raise GraphError(f'{qid}: an explicit route needs concept references.')
        if 'methodDirectNodeIds' in route:
            _object(route['methodDirectNodeIds'], f'{qid}.route.methodDirectNodeIds')
            for method_id, direct in route['methodDirectNodeIds'].items():
                _text(method_id, f'{qid}.route.methodId')
                _strings(direct, f'{qid}.route.methodDirectNodeIds', ids=set(route['nodeIds']))
            _strings(route.get('contextNodeIds'), f'{qid}.route.contextNodeIds', ids=set(route['nodeIds']))
            immediate = {node for ids in route['methodDirectNodeIds'].values() for node in ids}
            if route['contextNodeIds'] != [node for node in route['nodeIds'] if node not in immediate]:
                raise GraphError(f'{qid}: route context must remain separate from immediate method concepts.')
    if mapping['status'] == 'mapped' and not mapping['assessedIds'] and not routes:
        raise GraphError(f'{qid}: a mapped question needs an assessed concept or a complete solution route.')


def _requires_cycles(relationships):
    adjacency = {}
    for row in relationships:
        if row['status'] == 'accepted' and row['relation'] == 'requires':
            adjacency.setdefault(row['nodeId'], []).append(row['prerequisiteId'])
    visiting, visited = set(), set()
    # Iterative DFS supports a full source graph without Python recursion limits.
    for start in sorted(adjacency):
        stack = [(start, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                visiting.remove(node)
                visited.add(node)
            elif node in visiting:
                raise GraphError(f'Accepted requires cycle reaches {node}.')
            elif node not in visited:
                visiting.add(node)
                stack.append((node, True))
                stack.extend((other, False) for other in sorted(adjacency.get(node, []), reverse=True))


def _validate_source(source):
    _object(source['metadata'], 'metadata')
    for field in ('nodes', 'relationships', 'mappings'):
        if not isinstance(source[field], list):
            raise GraphError(f'{field}: expected an array.')
    ids = set()
    for node in source['nodes']:
        _object(node, 'node')
        for field in ('id', 'name', 'description', 'reviewStatus'):
            _text(node.get(field), f'node.{field}')
        if node['id'] in ids:
            raise GraphError(f'Duplicate node ID {node["id"]}.')
        ids.add(node['id'])
        if node.get('kind') not in {'concept', 'procedure', 'synthesis'}:
            raise GraphError(f'{node["id"]}: invalid kind.')
        _strings(node.get('criteria'), f'{node["id"]}.criteria')
        _strings(node.get('aliases'), f'{node["id"]}.aliases')
    relationship_ids, accepted_relations = set(), set()
    for row in source['relationships']:
        _object(row, 'relationship')
        for field in ('id', 'nodeId', 'prerequisiteId', 'scope', 'reason', 'reviewStatus'):
            _text(row.get(field), f'relationship.{field}')
        if row['id'] in relationship_ids:
            raise GraphError(f'Duplicate relationship ID {row["id"]}.')
        relationship_ids.add(row['id'])
        if row['nodeId'] not in ids or row['prerequisiteId'] not in ids:
            raise GraphError(f'{row["id"]}: unknown relationship endpoint.')
        if row.get('relation') not in RELATIONS or row.get('status') not in STATUSES:
            raise GraphError(f'{row["id"]}: invalid relation or status.')
        if row.get('methodId') is not None:
            _text(row['methodId'], f'{row["id"]}.methodId')
        if row['relation'] == 'method_component' and not row.get('methodId'):
            raise GraphError(f'{row["id"]}: method_component requires methodId.')
        if row['status'] == 'accepted':
            signature = tuple(row.get(k) for k in ('nodeId', 'prerequisiteId', 'relation', 'methodId', 'scope'))
            if signature in accepted_relations:
                raise GraphError(f'{row["id"]}: duplicate accepted relationship.')
            accepted_relations.add(signature)
        _object(row.get('original'), f'{row["id"]}.original')
        _reviews(row.get('reviews'), f'{row["id"]}.reviews')
    import curriculum_graph
    curriculum_graph.validate_source(source.get('curricula', {'schemaVersion': 1, 'layers': []}), source.get('alignments', []), ids)
    _requires_cycles(source['relationships'])
    question_ids = set()
    for mapping in source['mappings']:
        validate_mapping(mapping, ids)
        if mapping['questionId'] in question_ids:
            raise GraphError(f'Duplicate question mapping {mapping["questionId"]}.')
        question_ids.add(mapping['questionId'])


def load_source(root=ROOT, source_dir=None):
    """Load public sources and an optional sibling local/mappings.jsonl overlay.

    Both sets are equally strict about IDs, duplicates and installed-content
    bindings. An absent local overlay means only the public mappings are built.
    An explicit source_dir uses its own sibling local directory, not another
    checkout's local records.
    """
    source_dir = Path(source_dir) if source_dir is not None else database_root(root) / 'knowledge-graph/source'
    try:
        source = {key: json.loads((source_dir / (key + '.json')).read_text(encoding='utf-8-sig'))
                  for key in ('metadata', 'nodes', 'relationships')}
        source['mappings'] = [json.loads(line) for line in (source_dir / 'mappings.jsonl').read_text(
            encoding='utf-8-sig').splitlines() if line.strip()]
        local_mappings = source_dir.parent / 'local/mappings.jsonl'
        if local_mappings.is_file():
            source['mappings'].extend(json.loads(line) for line in local_mappings.read_text(
                encoding='utf-8-sig').splitlines() if line.strip())
        import curriculum_graph
        source['curricula'], source['alignments'] = curriculum_graph.load_optional(source_dir, {n['id'] for n in source['nodes']})
        _validate_source(source)
        return source
    except (OSError, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, GraphError):
            raise
        raise GraphError(f'Cannot read graph source: {exc}') from None


def _source_digest(source):
    return _digest({'metadata': source['metadata'],
                    'nodes': sorted(source['nodes'], key=lambda x: x['id']),
                    'relationships': sorted(source['relationships'], key=lambda x: x['id']),
                    'mappings': sorted(source['mappings'], key=lambda x: x['questionId']),
                    'curricula': _normalized_curricula(source.get('curricula', {'schemaVersion': 1, 'layers': []})),
                    'alignments': sorted(source.get('alignments', []), key=lambda x: x['id'])})


def _normalized_curricula(curricula):
    return {**curricula, 'layers': [{**layer,
        'nodes': sorted(layer['nodes'], key=lambda n: n['id']),
        'relationships': sorted(layer['relationships'], key=lambda e: e['id'])}
        for layer in sorted(curricula['layers'], key=lambda l: l['id'])]}


def source_digest(root=ROOT, source_dir=None):
    """Identity of current validated public sources and the optional local overlay."""
    return _source_digest(load_source(root, source_dir))


def _version(metadata):
    return str(metadata.get('version') or metadata.get('graphVersion') or metadata.get('schemaVersion') or '1')


DDL = '''
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE nodes (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
 review_status TEXT NOT NULL, raw_json TEXT NOT NULL);
CREATE TABLE relationships (id TEXT PRIMARY KEY, node_id TEXT NOT NULL REFERENCES nodes(id),
 prerequisite_id TEXT NOT NULL REFERENCES nodes(id), relation TEXT NOT NULL,
 status TEXT NOT NULL, method_id TEXT, raw_json TEXT NOT NULL);
CREATE INDEX relationships_dependent ON relationships(node_id,status,relation);
CREATE INDEX relationships_prerequisite ON relationships(prerequisite_id,status,relation);
CREATE TABLE questions (question_id TEXT PRIMARY KEY, bank TEXT NOT NULL, content_hash TEXT NOT NULL,
 status TEXT NOT NULL, review_status TEXT NOT NULL, raw_json TEXT NOT NULL);
CREATE TABLE question_nodes (question_id TEXT NOT NULL REFERENCES questions(question_id),
 node_id TEXT NOT NULL REFERENCES nodes(id), role TEXT NOT NULL, position INTEGER NOT NULL,
 PRIMARY KEY(question_id,role,node_id));
CREATE INDEX question_nodes_node ON question_nodes(node_id);
CREATE TABLE routes (question_id TEXT NOT NULL REFERENCES questions(question_id), id TEXT NOT NULL,
 label TEXT NOT NULL, position INTEGER NOT NULL, raw_json TEXT NOT NULL, PRIMARY KEY(question_id,id));
CREATE TABLE route_nodes (question_id TEXT NOT NULL, route_id TEXT NOT NULL,
 node_id TEXT NOT NULL REFERENCES nodes(id), position INTEGER NOT NULL,
 PRIMARY KEY(question_id,route_id,node_id), FOREIGN KEY(question_id,route_id) REFERENCES routes(question_id,id));
CREATE INDEX route_nodes_node ON route_nodes(node_id);
CREATE TABLE relationship_reviews (relationship_id TEXT NOT NULL REFERENCES relationships(id),
 position INTEGER NOT NULL, raw_json TEXT NOT NULL, PRIMARY KEY(relationship_id,position));
CREATE TABLE mapping_reviews (question_id TEXT NOT NULL REFERENCES questions(question_id),
 position INTEGER NOT NULL, raw_json TEXT NOT NULL, PRIMARY KEY(question_id,position));
'''


def _db_path(root, db_path):
    return Path(db_path) if db_path is not None else database_root(root) / 'knowledge-graph/knowledge.sqlite3'


def _connect_readonly(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA query_only=ON')
    return connection


def node_ids(root=ROOT, db_path=None):
    try:
        with closing(_connect_readonly(_db_path(root, db_path))) as connection:
            return frozenset(row['id'] for row in connection.execute('SELECT id FROM nodes'))
    except (sqlite3.Error, OSError) as exc:
        raise GraphError(f'Cannot read graph nodes: {exc}') from None


def graph_version(root=ROOT, db_path=None):
    try:
        with closing(_connect_readonly(_db_path(root, db_path))) as connection:
            row = connection.execute('SELECT value FROM metadata WHERE key=?', ('graphVersion',)).fetchone()
            if row is None:
                raise GraphError('Graph version is missing.')
            return row[0]
    except (sqlite3.Error, OSError) as exc:
        raise GraphError(f'Cannot read graph version: {exc}') from None


def mapping_record(question_id, root=ROOT, db_path=None):
    """Return retained authoritative mapping data, or None for an unknown item."""
    try:
        with closing(_connect_readonly(_db_path(root, db_path))) as connection:
            row = connection.execute('SELECT raw_json FROM questions WHERE question_id=?', (question_id,)).fetchone()
            return json.loads(row[0]) if row else None
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise GraphError(f'Cannot read graph mapping: {exc}') from None


def _source_from_db(connection):
    meta = dict(connection.execute('SELECT key,value FROM metadata'))
    source = {'metadata': json.loads(meta['sourceMetadata'])}
    for key, table, order in (('nodes', 'nodes', 'id'), ('relationships', 'relationships', 'id'),
                              ('mappings', 'questions', 'question_id')):
        source[key] = [json.loads(row[0]) for row in connection.execute(f'SELECT raw_json FROM {table} ORDER BY {order}')]
    import curriculum_graph
    source['curricula'], source['alignments'] = curriculum_graph.source_from_db(connection)
    return source, meta


def _binding(mapping, question, root):
    if question.get('ID') != mapping['questionId'] or question.get('Bank') != mapping['bank']:
        raise GraphError(f'{mapping["questionId"]}: question bank/identity mismatch.')
    actual = question_fingerprint(question, root)
    if actual['contentHash'] != mapping['contentHash'] or actual['figureHashes'] != mapping['figureHashes']:
        raise GraphError(f'{mapping["questionId"]}: stale content or figure binding.')
    validate_heading_context(mapping, question)
    if 'headingContext' in mapping:
        actual['headingContext'] = mapping['headingContext']
    return actual


def validate_heading_context(mapping, question):
    """Bind a visible topic heading only when the task actually refers to it.

    Ordinary source tags remain outside the mathematical binding. A question
    asking about 'the criterion' may need the topic title shown in the UI.
    """
    if 'headingContext' in mapping:
        topic = question.get('Topic')
        if not isinstance(topic, dict) or topic.get('label') != mapping['headingContext']:
            raise GraphError(f'{mapping.get("questionId", question.get("ID"))}: stale visible heading context.')


def _logical_digest(connection):
    tables = ('metadata', 'nodes', 'relationships', 'questions', 'question_nodes', 'routes',
              'route_nodes', 'relationship_reviews', 'mapping_reviews', 'curriculum_layers',
              'curriculum_nodes', 'curriculum_relationships', 'concept_alignments')
    return _digest({table: sorted([list(row) for row in connection.execute(f'SELECT * FROM {table}')], key=_json)
                    for table in tables})


def _validate_connection(connection, root, check_bindings):
    if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise GraphError('SQLite integrity check failed.')
    if connection.execute('PRAGMA foreign_key_check').fetchall():
        raise GraphError('SQLite foreign key check failed.')
    source, metadata = _source_from_db(connection)
    _validate_source(source)
    if (metadata.get('schemaVersion') != SCHEMA_VERSION
            or metadata.get('graphVersion') != _version(source['metadata'])
            or metadata.get('sourceDigest') != _source_digest(source)):
        raise GraphError('Database source identity does not match its stored records.')
    import curriculum_graph
    curriculum_graph.validate_index(connection, source)
    # Check indexed columns against retained source records, including route and review rows.
    expected_counts = {'question_nodes': 0, 'routes': 0, 'route_nodes': 0,
                       'mapping_reviews': 0, 'relationship_reviews': 0}
    for node in source['nodes']:
        row = connection.execute('SELECT name,kind,review_status FROM nodes WHERE id=?', (node['id'],)).fetchone()
        if tuple(row) != (node['name'], node['kind'], node['reviewStatus']):
            raise GraphError(f'{node["id"]}: node index differs from source.')
    for edge in source['relationships']:
        row = connection.execute('SELECT node_id,prerequisite_id,relation,status,method_id FROM relationships WHERE id=?', (edge['id'],)).fetchone()
        if tuple(row) != tuple(edge.get(k) for k in ('nodeId', 'prerequisiteId', 'relation', 'status', 'methodId')):
            raise GraphError(f'{edge["id"]}: relationship index differs from source.')
        reviews = [json.loads(row[0]) for row in connection.execute('SELECT raw_json FROM relationship_reviews WHERE relationship_id=? ORDER BY position', (edge['id'],))]
        if reviews != edge['reviews']:
            raise GraphError(f'{edge["id"]}: relationship review history differs.')
        expected_counts['relationship_reviews'] += len(reviews)
    for mapping in source['mappings']:
        qid = mapping['questionId']
        row = connection.execute('SELECT bank,content_hash,status,review_status FROM questions WHERE question_id=?', (qid,)).fetchone()
        if tuple(row) != tuple(mapping[k] for k in ('bank', 'contentHash', 'status', 'reviewStatus')):
            raise GraphError(f'{qid}: mapping index differs from source.')
        for role, field in (('assessed', 'assessedIds'), ('support', 'supportIds'), ('contextual', 'contextualIds')):
            actual = [row[0] for row in connection.execute('SELECT node_id FROM question_nodes WHERE question_id=? AND role=? ORDER BY position', (qid, role))]
            if actual != mapping.get(field, []):
                raise GraphError(f'{qid}: {role} index differs from source.')
            expected_counts['question_nodes'] += len(actual)
        routes = [json.loads(row[0]) for row in connection.execute('SELECT raw_json FROM routes WHERE question_id=? ORDER BY position', (qid,))]
        if routes != mapping['routes']:
            raise GraphError(f'{qid}: route index differs from source.')
        expected_counts['routes'] += len(routes)
        for route in routes:
            row = connection.execute('SELECT label FROM routes WHERE question_id=? AND id=?', (qid, route['id'])).fetchone()
            actual = [row[0] for row in connection.execute('SELECT node_id FROM route_nodes WHERE question_id=? AND route_id=? ORDER BY position', (qid, route['id']))]
            if row[0] != route['label'] or actual != route['nodeIds']:
                raise GraphError(f'{qid}: route nodes differ from source.')
            expected_counts['route_nodes'] += len(actual)
        reviews = [json.loads(row[0]) for row in connection.execute('SELECT raw_json FROM mapping_reviews WHERE question_id=? ORDER BY position', (qid,))]
        if reviews != mapping['reviews']:
            raise GraphError(f'{qid}: mapping review history differs.')
        expected_counts['mapping_reviews'] += len(reviews)
        if check_bindings:
            _binding(mapping, load_question(qid, root), root)
    for table, expected in expected_counts.items():
        if connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] != expected:
            raise GraphError(f'{table}: unexpected indexed rows.')
    return {'valid': True, 'schemaVersion': SCHEMA_VERSION, 'graphVersion': metadata['graphVersion'],
            'sourceDigest': metadata['sourceDigest'], 'logicalDigest': _logical_digest(connection),
            'nodes': len(source['nodes']), 'relationships': len(source['relationships']),
            'mappings': len(source['mappings']),
            'mapped': sum(m['status'] == 'mapped' for m in source['mappings']),
            'non_diagnostic': sum(m['status'] == 'non_diagnostic' for m in source['mappings']),
            'unresolved': sum(m['status'] == 'unresolved' for m in source['mappings']),
            'completedMappings': sum(m['status'] in {'mapped', 'non_diagnostic'} for m in source['mappings']),
            'bindingsChecked': len(source['mappings']) if check_bindings else 0}


def validate_database(root=ROOT, db_path=None, *, check_bindings=True):
    try:
        with closing(_connect_readonly(_db_path(root, db_path))) as connection:
            return _validate_connection(connection, Path(root), check_bindings)
    except (sqlite3.Error, OSError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, GraphError):
            raise
        raise GraphError(f'Cannot validate graph database: {exc}') from None


def _install_database(temporary, destination, *, wait_seconds=60):
    """Keep the old graph available while a Windows reader finishes its query."""
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            os.replace(temporary, destination)
            return
        except PermissionError as exc:
            if (os.name != 'nt' or getattr(exc, 'winerror', None) not in (5, 32, 33)
                    or not destination.is_file() or time.monotonic() >= deadline):
                raise
            time.sleep(0.25)


def build_database(root=ROOT, source_dir=None, db_path=None, *, check_bindings=True):
    """Validate sources, build beside the destination, verify, then atomically replace."""
    root = Path(root)
    source = load_source(root, source_dir)
    destination = _db_path(root, db_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.knowledge-', suffix='.sqlite3', dir=destination.parent)
    os.close(handle)
    try:
        with sqlite3.connect(temporary) as connection:
            connection.execute('PRAGMA foreign_keys=ON')
            connection.executescript(DDL)
            import curriculum_graph
            connection.executescript(curriculum_graph.DDL)
            metadata = {'schemaVersion': SCHEMA_VERSION, 'graphVersion': _version(source['metadata']),
                        'sourceDigest': _source_digest(source), 'sourceMetadata': _json(source['metadata'])}
            connection.executemany('INSERT INTO metadata VALUES (?,?)', sorted(metadata.items()))
            for node in sorted(source['nodes'], key=lambda x: x['id']):
                connection.execute('INSERT INTO nodes VALUES (?,?,?,?,?)',
                                   (node['id'], node['name'], node['kind'], node['reviewStatus'], _json(node)))
            for edge in sorted(source['relationships'], key=lambda x: x['id']):
                connection.execute('INSERT INTO relationships VALUES (?,?,?,?,?,?,?)',
                                   (edge['id'], edge['nodeId'], edge['prerequisiteId'], edge['relation'],
                                    edge['status'], edge.get('methodId'), _json(edge)))
                connection.executemany('INSERT INTO relationship_reviews VALUES (?,?,?)',
                                       [(edge['id'], i, _json(r)) for i, r in enumerate(edge['reviews'])])
            for mapping in sorted(source['mappings'], key=lambda x: x['questionId']):
                qid = mapping['questionId']
                connection.execute('INSERT INTO questions VALUES (?,?,?,?,?,?)',
                                   (qid, mapping['bank'], mapping['contentHash'], mapping['status'],
                                    mapping['reviewStatus'], _json(mapping)))
                for role, field in (('assessed', 'assessedIds'), ('support', 'supportIds'), ('contextual', 'contextualIds')):
                    connection.executemany('INSERT INTO question_nodes VALUES (?,?,?,?)',
                                           [(qid, node, role, i) for i, node in enumerate(mapping.get(field, []))])
                for i, route in enumerate(mapping['routes']):
                    connection.execute('INSERT INTO routes VALUES (?,?,?,?,?)', (qid, route['id'], route['label'], i, _json(route)))
                    connection.executemany('INSERT INTO route_nodes VALUES (?,?,?,?)',
                                           [(qid, route['id'], node, j) for j, node in enumerate(route['nodeIds'])])
                connection.executemany('INSERT INTO mapping_reviews VALUES (?,?,?)',
                                       [(qid, i, _json(r)) for i, r in enumerate(mapping['reviews'])])
            curriculum_graph.insert_source(connection, source)
            connection.commit()
            report = _validate_connection(connection, root, check_bindings)
        # Context managers commit but do not close SQLite connections.
        connection.close()
        _install_database(temporary, destination)
        return report
    finally:
        if 'connection' in locals():
            connection.close()
        if os.path.exists(temporary):
            os.unlink(temporary)


def _empty(question, status, reason):
    return {'status': status, 'reason': reason, 'questionId': question.get('ID'),
            'nodes': [], 'edges': [], 'routes': [], 'omissions': {'nodes': 0, 'edges': 0, 'routes': 0}}


def _node_summary(node, roles):
    result = {**{key: node.get(key) for key in ('id', 'name', 'nameZh', 'description', 'criteria', 'kind', 'reviewStatus')},
              'roles': roles}
    if node.get('scopeNotes'):
        result['scopeNotes'] = node['scopeNotes']
    return result


def _edge_summary(edge):
    return {key: edge.get(key) for key in ('id', 'nodeId', 'prerequisiteId', 'relation', 'methodId', 'scope', 'reason', 'reviewStatus')}


def _contextual_definitions(result, mapping, connection, max_nodes, max_chars):
    """Add only explicit definitions, without using them as traversal seeds."""
    if 'contextualIds' not in mapping:
        return result
    ids = mapping['contextualIds']
    result.update(contextualIds=list(ids), contextualNodes=[])
    result['omissions']['contextualNodes'] = len(ids)
    available = max(0, max_nodes - len(result['nodes']))
    for node_id in ids[:available]:
        row = connection.execute('SELECT raw_json FROM nodes WHERE id=?', (node_id,)).fetchone()
        if row is None:
            raise GraphError(f'{node_id}: contextual definition missing.')
        result['contextualNodes'].append(_node_summary(json.loads(row[0]), ['contextual']))
        result['omissions']['contextualNodes'] -= 1
    while result['contextualNodes'] and len(_json(result)) > max_chars:
        result['contextualNodes'].pop()
        result['omissions']['contextualNodes'] += 1
    if len(_json(result)) > max_chars:
        result['contextualIds'] = []
        result['omissions']['contextualIds'] = len(ids)
    return result


def _compact_current(question, status, reason, mapping, binding, max_chars, **fields):
    """Keep bound adjudication status even when mathematical context is omitted."""
    result = _empty(question, status, reason)
    result.update(fields)
    result.update(binding={'status': 'current', 'contentHash': binding['contentHash']},
                  answerCheck=mapping['answerCheck'], flags=mapping['flags'])
    if len(_json(result)) > max_chars:
        result['answerCheck'] = {key: mapping['answerCheck'][key] for key in ('status',)
                                 if key in mapping['answerCheck']}
        result['omissions']['answerCheckDetails'] = len(result['answerCheck']) < len(mapping['answerCheck'])
    if len(_json(result)) > max_chars:
        result['omissions']['flags'] = len(result['flags'])
        result['flags'] = []
    if len(_json(result)) > max_chars:
        result.pop('graphVersion', None)
        result.pop('reviewStatus', None)
    return result


def context_for_question(question, root=ROOT, max_nodes=DEFAULT_MAX_NODES, max_chars=DEFAULT_MAX_CHARS, depth=1, *, dependents=False, layer='ailleo', selected_node_id=None):
    """Return bounded, deterministic current context, or an explicit missing/stale state.

    Rejected/unresolved edges never enter normal retrieval. requires/prepares
    traverse toward prerequisites. A method_component is included only when its
    prerequisite is explicitly in a question route and its dependent is explicitly
    mapped to the question. It never expands to an undeclared method node.
    applicableRouteIds link the retained edge to complete question route groups;
    question route IDs need not equal the graph review's method identity.
    """
    import curriculum_graph
    from question_format_v3 import normalize_question
    question = normalize_question(question, root=root)
    curriculum_graph._layer(layer)
    if not isinstance(depth, int) or not 0 <= depth <= 20:
        raise GraphError('Depth must be an integer between 0 and 20.')
    result = _context_for_question(question, root, max_nodes, max_chars,
                                  depth if layer == 'ailleo' else 0, dependents=dependents)
    seeds = list(dict.fromkeys(result.get('assessedIds', []) +
                 [n for route in result.get('routes', []) for n in route['nodeIds']]))
    selected_node_id = selected_node_id or None
    selection = None
    matched_seeds = []
    selected_routes = []
    priority_routes = []
    if selected_node_id is not None:
        # Budget omission must not turn a bound browse selection into an
        # unrelated topic. Match the full current mapping, then reserve its
        # whole route if the default written methods crowded that route out.
        full_seeds, mapping = seeds, None
        if result.get('status') == 'mapped' and result.get('binding', {}).get('status') == 'current':
            mapping = mapping_record(question.get('ID'), root)
            if mapping is not None:
                _binding(mapping, question, root)
                full_seeds = list(dict.fromkeys(mapping['assessedIds'] +
                             [n for route in mapping['routes'] for n in route['nodeIds']]))
        matched = curriculum_graph.matching_selection(layer, selected_node_id, full_seeds, root)
        matched_seeds = [node_id for node_id in seeds if node_id in matched]
        if matched and mapping is not None:
            selected_routes = [route['id'] for route in mapping['routes'] if set(route['nodeIds']) & set(matched)]
        if matched and not matched_seeds and mapping is not None:
            if selected_routes:
                priority_routes = selected_routes
                result = _context_for_question(question, root, max_nodes, max_chars,
                                              depth if layer == 'ailleo' else 0, dependents=dependents,
                                              priority_route_ids=selected_routes)
                seeds = list(dict.fromkeys(result.get('assessedIds', []) +
                             [n for route in result.get('routes', []) for n in route['nodeIds']]))
                matched_seeds = [node_id for node_id in seeds if node_id in matched]
        selection = {'layer': layer, 'nodeId': selected_node_id,
                     'status': 'matched' if matched else 'unrelated_to_question',
                     'meaning': 'Selected scope is used only when its accepted crosswalk matches bound question concepts; otherwise question alignments apply.'}
        if matched and not matched_seeds:
            selection['contextStatus'] = 'bounded_omission'

    def reserve_selection(field, value):
        # Reserve only a compact scope marker, not native background or a
        # preferred proof. The core reader can then shed extra context before
        # it needs to omit a complete route.
        nonlocal result, seeds, matched_seeds
        reserved = deepcopy(value)
        marker = reserved if field == 'curriculumSelection' else reserved['selection']
        if matched:
            marker['contextStatus'] = 'bounded_omission'
        overhead = len(_json({field: reserved})) - 1
        result = _context_for_question(question, root, max_nodes, max_chars,
                                      depth if layer == 'ailleo' else 0, dependents=dependents,
                                      priority_route_ids=priority_routes, reserved_chars=overhead)
        seeds = list(dict.fromkeys(result.get('assessedIds', []) +
                     [n for route in result.get('routes', []) for n in route['nodeIds']]))
        matched_seeds = [node_id for node_id in seeds if node_id in matched]
        if matched and not matched_seeds and selected_routes and not priority_routes:
            result = _context_for_question(question, root, max_nodes, max_chars,
                                          depth if layer == 'ailleo' else 0, dependents=dependents,
                                          priority_route_ids=selected_routes, reserved_chars=overhead)
            seeds = list(dict.fromkeys(result.get('assessedIds', []) +
                         [n for route in result.get('routes', []) for n in route['nodeIds']]))
            matched_seeds = [node_id for node_id in seeds if node_id in matched]
        selection.pop('contextStatus', None)
        if matched and not matched_seeds:
            selection['contextStatus'] = 'bounded_omission'
        if (len(_json({**result, field: value})) > max_chars
                and result.get('reason') == 'context_character_budget'):
            # The omission counts already explain this empty bounded context.
            # Keep its binding and answer-review status before a duplicate label.
            result.pop('reason')

    if layer == 'ailleo':
        if selection:
            if len(_json({**result, 'curriculumSelection': selection})) > max_chars:
                selection.pop('meaning')
            if len(_json({**result, 'curriculumSelection': selection})) > max_chars:
                reserve_selection('curriculumSelection', selection)
            result['curriculumSelection'] = selection
        return result
    # Keep mathematical question bindings and complete retained routes first.
    # The selected curriculum supplies its own connections, without ailleo edges.
    result['omissions']['edges'] += len(result.get('edges', []))
    result['edges'] = []
    supplement = {'layer': layer, 'status': 'omitted', 'neighborhoods': [],
                  'maxNativeNodes': min(max_nodes, 8),
                  'truncated': False, 'omissions': {'neighborhoods': 0},
                  'meaning': 'Direct native prerequisites and helpful preparation only; crosswalks do not establish prerequisites, mastery, or full coverage.'}
    if selection:
        supplement['selection'] = selection
        if len(_json({**result, 'curriculumContext': supplement})) > max_chars:
            selection.pop('meaning')
            supplement.pop('meaning')
        if len(_json({**result, 'curriculumContext': supplement})) > max_chars:
            reserve_selection('curriculumContext', supplement)
        if len(_json({**result, 'curriculumContext': supplement})) > max_chars:
            # At very small budgets keep the honest selected scope even when
            # the native neighborhood wrapper itself cannot fit.
            supplement = {'layer': layer, 'status': 'omitted', 'selection': selection}
            reserve_selection('curriculumContext', supplement)
            result['curriculumContext'] = supplement
            return result
    if len(_json({**result, 'curriculumContext': supplement})) > max_chars:
        return result
    result['curriculumContext'] = supplement
    if result.get('status') != 'mapped':
        supplement['status'] = 'unavailable'
        return result
    if matched_seeds:
        seeds = matched_seeds
    included_native_ids = set()
    for node_id in seeds:
        neighborhood = curriculum_graph.compact_tutor_prerequisites(
            node_id, layer, root, depth=min(depth, 1), limit=supplement['maxNativeNodes'],
            source_node_id=selected_node_id if matched_seeds else None, existing_node_ids=included_native_ids)
        if not neighborhood['nodes'] and neighborhood['truncated']:
            supplement['omissions']['neighborhoods'] += 1
            supplement['truncated'] = True
            continue
        candidate = deepcopy(supplement)
        candidate['neighborhoods'].append(neighborhood)
        statuses = [n['status'] for n in candidate['neighborhoods']]
        candidate['status'] = 'unmapped' if all(s == 'unmapped' for s in statuses) else ('mapped' if all(s == 'mapped' for s in statuses) else 'partial')
        while len(_json({**result, 'curriculumContext': candidate})) > max_chars and len(neighborhood['nodes']) > 1:
            removed = neighborhood['nodes'].pop()['id']
            neighborhood['omissions']['nodes'] += 1
            kept = [e for e in neighborhood['relationships'] if removed not in (e['fromId'], e['toId'])]
            neighborhood['omissions']['relationships'] += len(neighborhood['relationships']) - len(kept)
            neighborhood['relationships'] = kept
            neighborhood['alignments'] = [a for a in neighborhood['alignments'] if a['sourceNodeId'] != removed]
            neighborhood['truncated'] = True
            candidate['neighborhoods'][-1] = neighborhood
        if len(_json({**result, 'curriculumContext': candidate})) <= max_chars:
            candidate['truncated'] = candidate['truncated'] or neighborhood['truncated']
            supplement.update(candidate)
            included_native_ids.update(n['id'] for n in neighborhood['nodes'])
        else:
            supplement['omissions']['neighborhoods'] += 1
            supplement['truncated'] = True
    return result


def _solution_route_order(mapping, question):
    """Reserve current accepted written methods before retained alternatives.

    The central review must bind this exact solution and displayed task. A newer
    invalid solution review cannot revive an older review's route preference.
    Without that binding, retain the original deterministic source order.
    """
    routes = mapping['routes']
    if question.get('SchemaVersion') == '3.0':
        written = {m['id'] for m in question.get('SolutionMethods', []) if m.get('explanation')}
        return sorted(routes, key=lambda route: not (written & set(route.get('methodDirectNodeIds', {route['id']:[]}))))
    stage = {'amc': 'solution_bound_annotation', 'cn-math': 'cn_solution_bound_annotation'}.get(mapping['bank'])
    solution = question.get('Solution')
    if stage is None or not isinstance(solution, str) or not solution.strip():
        return routes
    review = next((r for r in reversed(mapping.get('reviews', [])) if r.get('stage') == stage), None)
    if (not review or review.get('decision') != 'accept'
            or review.get('questionContentHash') != mapping['contentHash']
            or review.get('solutionSHA256') != hashlib.sha256(solution.encode('utf-8')).hexdigest()):
        return routes
    methods = review.get('methodRouteIds')
    route_ids = {route['id'] for route in routes}
    if (not isinstance(methods, dict) or not methods
            or any(not isinstance(k, str) or not k or not isinstance(v, str) or v not in route_ids
                   for k, v in methods.items())):
        return routes
    written = set(methods.values())
    return sorted(routes, key=lambda route: route['id'] not in written)


def _context_for_question(question, root, max_nodes, max_chars, depth, *, dependents=False,
                          preferred_route=None, priority_route_ids=(), reserved_chars=0):
    if not isinstance(question, dict):
        return _empty({}, 'missing', 'invalid_question')
    if not isinstance(max_nodes, int) or max_nodes < 1 or not isinstance(max_chars, int) or max_chars < 512:
        raise GraphError('Context limits require max_nodes >= 1 and max_chars >= 512.')
    if not isinstance(depth, int) or not 0 <= depth <= 20:
        raise GraphError('Depth must be an integer between 0 and 20.')
    budget = max_chars - reserved_chars
    db = _db_path(root, None)
    if not db.is_file():
        return _empty(question, 'missing', 'database_missing')
    connection = None
    try:
        connection = _connect_readonly(db)
        meta = dict(connection.execute('SELECT key,value FROM metadata'))
        if meta.get('schemaVersion') != SCHEMA_VERSION:
            return _empty(question, 'missing', 'unsupported_database_version')
        row = connection.execute('SELECT raw_json FROM questions WHERE question_id=?', (question.get('ID'),)).fetchone()
        if row is None:
            return _empty(question, 'missing', 'mapping_missing')
        mapping = json.loads(row[0])
        try:
            binding = _binding(mapping, question, root)
        except GraphError:
            return _empty(question, 'stale', 'content_or_figure_binding_changed')
        embedded = question.get('KnowledgeGraph')
        if embedded is not None:
            expected = {key: mapping[key] for key in ('contentHash', 'status', 'reviewStatus', 'assessedIds', 'supportIds', 'routes', 'flags')}
            expected['version'] = meta['graphVersion']
            if 'headingContext' in mapping:
                expected['headingContext'] = mapping['headingContext']
            if (not isinstance(embedded, dict) or any(embedded.get(k) != v for k, v in expected.items())
                    or embedded.get('contextualIds', []) != mapping.get('contextualIds', [])):
                # A stale projection cannot steer mathematical retrieval, but it
                # cannot override a central adjudication bound to this unchanged
                # question either. Actual content/figure drift was rejected above.
                result = _empty(question, 'stale', 'question_graph_metadata_changed')
                result.update(binding={'status': 'current', **binding},
                              answerCheck=mapping['answerCheck'], flags=mapping['flags'])
                if len(_json(result)) > budget:
                    return _compact_current(question, 'stale', 'question_graph_metadata_changed',
                                            mapping, binding, budget)
                return result
        if mapping['status'] == 'non_diagnostic':
            result = _empty(question, 'non_diagnostic', 'answer_relation_supplied')
            result.update(reviewStatus=mapping['reviewStatus'], graphVersion=meta['graphVersion'],
                          binding={'status': 'current', **binding}, assessedIds=[], supportIds=[],
                          answerCheck=mapping['answerCheck'], flags=mapping['flags'],
                          meaning=NON_DIAGNOSTIC_MEANING)
            _contextual_definitions(result, mapping, connection, max_nodes, budget)
            if len(_json(result)) > budget:
                return _compact_current(question, 'non_diagnostic', 'answer_relation_supplied', mapping,
                                        binding, budget, contextualIds=[], contextualNodes=[],
                                        omissions={'nodes': 0, 'edges': 0, 'routes': 0,
                                                   'contextualNodes': len(mapping['contextualIds'])})
            return result
        if mapping['status'] != 'mapped':
            result = _empty(question, 'unresolved', 'mapping_needs_review')
            result.update(reviewStatus=mapping['reviewStatus'], binding={'status': 'current', **binding},
                          answerCheck=mapping['answerCheck'], flags=mapping['flags'])
            if len(_json(result)) > budget:
                return _compact_current(question, 'unresolved', 'mapping_needs_review', mapping,
                                        binding, budget, reviewStatus=mapping['reviewStatus'])
            return result
        ordered_routes = _solution_route_order(mapping, question)
        if priority_route_ids:
            ordered_routes = sorted(ordered_routes, key=lambda route: route['id'] not in priority_route_ids)
        roles, seeds = {}, []
        for field, role in (('assessedIds', 'assessed'), ('supportIds', 'support')):
            for node_id in mapping[field]:
                if node_id not in roles:
                    seeds.append(node_id)
                    roles[node_id] = []
                roles[node_id].append(role)
        for route in ordered_routes:
            for node_id in route['nodeIds']:
                if node_id not in roles:
                    seeds.append(node_id)
                    roles[node_id] = []
                roles[node_id].append('route:' + route['id'])
        universal_nodes = set(mapping['assessedIds']) | set(mapping['supportIds'])
        # Reserve whole alternatives before spending the node budget. A larger
        # first route must not crowd out a later complete route that fits. Do not
        # expand fragments of omitted routes at the expense of retained routes'
        # prerequisites; their explicit seeds still count as omitted candidates.
        selected_seeds = set(universal_nodes)
        for route in ordered_routes:
            if preferred_route is not None and route['id'] != preferred_route:
                continue
            candidate = selected_seeds | set(route['nodeIds'])
            if len(candidate) <= max_nodes:
                selected_seeds = candidate
        omitted_seeds = set(seeds) - selected_seeds
        seeds = [node_id for node_id in seeds if node_id in selected_seeds]
        route_nodes = {route['id']: set(route['nodeIds']) for route in mapping['routes']}
        routes_by_node = {}
        for route in mapping['routes']:
            for node_id in route['nodeIds']:
                routes_by_node.setdefault(node_id, []).append(route['id'])
        summaries, candidate_edges = {}, {}
        queue = deque((node_id, 0) for node_id in seeds)
        visited, omitted_ids = set(), set(omitted_seeds)
        while queue:
            node_id, distance = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            node_row = connection.execute('SELECT raw_json FROM nodes WHERE id=?', (node_id,)).fetchone()
            if node_row is None:
                return _empty(question, 'stale', 'mapping_node_missing')
            if len(summaries) >= max_nodes:
                omitted_ids.add(node_id)
                continue
            summaries[node_id] = _node_summary(json.loads(node_row[0]), roles.get(node_id, ['dependent' if dependents else 'prerequisite']))
            omitted_ids.discard(node_id)
            if distance >= depth:
                continue
            column = 'prerequisite_id' if dependents else 'node_id'
            rows = connection.execute(f'SELECT raw_json FROM relationships WHERE {column}=? AND status=? ORDER BY CASE relation WHEN \'requires\' THEN 0 WHEN \'prepares\' THEN 1 ELSE 2 END,id', (node_id, 'accepted'))
            for edge_row in rows:
                edge = json.loads(edge_row[0])
                if edge['relation'] == 'related':
                    continue
                summary = _edge_summary(edge)
                if edge['relation'] == 'method_component':
                    applicable_routes = [route_id for route_id in routes_by_node.get(edge['prerequisiteId'], [])
                                         if edge['nodeId'] in universal_nodes or edge['nodeId'] in route_nodes[route_id]]
                    if not applicable_routes:
                        continue
                    summary['applicableRouteIds'] = list(applicable_routes)
                    candidate_edges[edge['id']] = summary
                    continue
                candidate_edges[edge['id']] = summary
                next_id = edge['nodeId'] if dependents else edge['prerequisiteId']
                queue.append((next_id, distance + 1))
        result = {'status': 'mapped', 'questionId': mapping['questionId'], 'graphVersion': meta['graphVersion'],
                  'sourceDigest': meta['sourceDigest'], 'reviewStatus': mapping['reviewStatus'],
                  'binding': {'status': 'current', **binding}, 'assessedIds': list(mapping['assessedIds']),
                  'supportIds': list(mapping['supportIds']), 'routes': ordered_routes,
                  'answerCheck': mapping['answerCheck'], 'flags': mapping['flags'],
                  'nodes': list(summaries.values()), 'edges': [], 'meaning': MEANING,
                  'omissions': {'nodes': len(omitted_ids), 'edges': 0, 'routes': 0,
                                'depth': depth, 'maxNodes': max_nodes, 'maxChars': max_chars,
                                'countsScope': 'Candidates reached within the requested depth; omitted branches are not expanded.'}}
        if 'contextualIds' in mapping:
            # Reserve the explicit context references before bounding the
            # mathematical neighborhood; definitions may only use room left over.
            result.update(contextualIds=list(mapping['contextualIds']), contextualNodes=[])
            result['omissions']['contextualNodes'] = len(mapping['contextualIds'])
        edges = sorted(candidate_edges.values(), key=lambda edge: (edge['nodeId'], edge['relation'], edge['prerequisiteId'], edge['id']))
        result['edges'] = [edge for edge in edges if edge['nodeId'] in summaries and edge['prerequisiteId'] in summaries]
        result['omissions']['edges'] = len(edges) - len(result['edges'])
        # Keep complete route groups or explicitly omit them. Never trim a route
        # into a different method, or retain an edge whose endpoint was removed.
        def reconcile_routes():
            included = {node['id'] for node in result['nodes']}
            result['routes'] = [route for route in ordered_routes if set(route['nodeIds']) <= included]
            result['omissions']['routes'] = len(mapping['routes']) - len(result['routes'])
            retained_routes = {route['id'] for route in result['routes']}
            kept_edges = []
            for edge in result['edges']:
                if edge['relation'] == 'method_component':
                    edge['applicableRouteIds'] = [route_id for route_id in edge['applicableRouteIds']
                                                  if route_id in retained_routes]
                    if not edge['applicableRouteIds']:
                        continue
                kept_edges.append(edge)
            result['omissions']['edges'] += len(result['edges']) - len(kept_edges)
            result['edges'] = kept_edges
            # A bounded-out alternative must not survive as a fragment labelled
            # with an absent route. Keep shared prerequisites reachable from the
            # retained assessed/support/complete-route seeds in this neighborhood.
            roots = set(mapping['assessedIds']) | set(mapping['supportIds'])
            roots.update(node_id for route in result['routes'] for node_id in route['nodeIds'])
            reachable = roots & included
            adjacency = {}
            for edge in result['edges']:
                if edge['relation'] != 'method_component':
                    start = edge['prerequisiteId'] if dependents else edge['nodeId']
                    end = edge['nodeId'] if dependents else edge['prerequisiteId']
                    adjacency.setdefault(start, []).append(end)
            pending = deque(sorted(reachable))
            while pending:
                for node_id in adjacency.get(pending.popleft(), []):
                    if node_id not in reachable:
                        reachable.add(node_id)
                        pending.append(node_id)
            kept_nodes = [node for node in result['nodes'] if node['id'] in reachable]
            result['omissions']['nodes'] += len(result['nodes']) - len(kept_nodes)
            result['nodes'] = kept_nodes
            for node in result['nodes']:
                node['roles'] = [role for role in node['roles']
                                 if not role.startswith('route:') or role[6:] in retained_routes]
                if not node['roles']:
                    node['roles'] = ['dependent' if dependents else 'prerequisite']
            kept_edges = [edge for edge in result['edges']
                          if edge['nodeId'] in reachable and edge['prerequisiteId'] in reachable]
            result['omissions']['edges'] += len(result['edges']) - len(kept_edges)
            result['edges'] = kept_edges
        reconcile_routes()
        complete_context = deepcopy(result) if result['routes'] else None
        while len(_json(result)) > budget and result['nodes']:
            if result['edges'] and any(result['nodes'][-1]['id'] in route['nodeIds']
                                       for route in result['routes']):
                # Do not lose a complete explicit method just to keep edge
                # detail. Commit this trade only if the retained definitions
                # fit; an oversized method must not consume every useful edge.
                edge_bounded = deepcopy(result)
                while len(_json(edge_bounded)) > budget and edge_bounded['edges']:
                    edge_bounded['edges'].pop()
                    edge_bounded['omissions']['edges'] += 1
                if len(_json(edge_bounded)) <= budget:
                    result = edge_bounded
                    reconcile_routes()
                    break
            removed = result['nodes'].pop()['id']
            result['omissions']['nodes'] += 1
            kept = [edge for edge in result['edges'] if removed not in (edge['nodeId'], edge['prerequisiteId'])]
            result['omissions']['edges'] += len(result['edges']) - len(kept)
            result['edges'] = kept
            reconcile_routes()
        if complete_context and not result['routes']:
            # Removing the last shared component can discard every alternative
            # after a longer earlier route consumed the budget. Try each whole
            # route with the universal concepts before giving up on all methods.
            trimmed = result
            for route in complete_context['routes']:
                needed = universal_nodes | set(route['nodeIds'])
                result = deepcopy(complete_context)
                result['nodes'] = [node for node in result['nodes'] if node['id'] in needed]
                result['edges'] = [edge for edge in result['edges']
                                   if {edge['nodeId'], edge['prerequisiteId']} <= needed]
                result['omissions']['nodes'] += len(complete_context['nodes']) - len(result['nodes'])
                result['omissions']['edges'] += len(complete_context['edges']) - len(result['edges'])
                reconcile_routes()
                # These nodes are all explicit universal/route roots. Preserve
                # their complete definitions and bound grading caveats before
                # supplementary relationship summaries when recovering a route.
                while result['routes'] and len(_json(result)) > budget and result['edges']:
                    result['edges'].pop()
                    result['omissions']['edges'] += 1
                if result['routes'] and len(_json(result)) <= budget:
                    break
            else:
                result = trimmed
        if preferred_route is None and mapping['routes'] and not result['routes']:
            # A route excluded by the initial combined node allocation may fit
            # individually after another alternative exceeds the character cap.
            # Retry only complete, individually node-bounded alternatives that
            # the character fallback above could not examine. This changes no
            # mapping or universal roles and makes no optimal-packing claim.
            tried = {route['id'] for route in complete_context['routes']} if complete_context else set()
            for route in ordered_routes:
                if route['id'] in tried or len(universal_nodes | set(route['nodeIds'])) > max_nodes:
                    continue
                alternative = _context_for_question(question, root, max_nodes, max_chars, depth,
                                                    dependents=dependents, preferred_route=route['id'],
                                                    priority_route_ids=priority_route_ids,
                                                    reserved_chars=reserved_chars)
                if alternative.get('routes'):
                    return alternative
        if len(_json(result)) > budget:
            # Extremely small budgets or unusually many explicit bindings still
            # receive a truthful bounded result, with no partial mathematical text.
            return _compact_current(question, 'mapped', 'context_character_budget', mapping,
                                    binding, budget, graphVersion=meta['graphVersion'],
                                    omissions={'nodes': len(summaries) + len(omitted_ids), 'edges': len(edges),
                                               'routes': len(mapping['routes']), 'maxChars': max_chars})
        return _contextual_definitions(result, mapping, connection, max_nodes, budget)
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError):
        return _empty(question, 'missing', 'database_unavailable')
    finally:
        if connection is not None:
            connection.close()


def format_context(result):
    """Keep method alternatives and grading qualifications visible in text output."""
    lines = [f'{result["questionId"]}: {result["status"]}']
    if result.get('reason'):
        lines.append('Context status: ' + result['reason'])
    if result.get('meaning'):
        lines.append(result['meaning'])
    answer_check = result.get('answerCheck', {})
    if answer_check:
        lines.append('Answer review: ' + answer_check.get('status', 'unspecified'))
        if answer_check.get('status') in {'confirmed_conflict', 'confirmed_ambiguous'}:
            lines.append('Grading: withheld because the reviewed question or answer is disputed.')
        if answer_check.get('reason'):
            lines.append('  ' + answer_check['reason'])
    for route in result.get('routes', []):
        lines.append(f'Optional route {route["id"]}: {route["label"]}; nodes: ' + ', '.join(route['nodeIds']))
    for field in ('nodes', 'contextualNodes'):
        for node in result.get(field, []):
            roles = 'context only' if field == 'contextualNodes' else ', '.join(node.get('roles', []))
            lines.append(f'  {node["id"]} [{roles}]: {node["name"]}. {node["description"]}')
            lines.append('    Review: ' + node.get('reviewStatus', 'unspecified'))
            for criterion in node.get('criteria', []):
                lines.append('    Criterion: ' + criterion)
            if node.get('scopeNotes'):
                notes = node['scopeNotes']
                lines.append('    Scope notes: ' + (notes if isinstance(notes, str) else _json(notes)))
    for edge in result['edges']:
        routes = edge.get('applicableRouteIds', [])
        qualifier = ' [routes: ' + ', '.join(routes) + ']' if routes else ''
        lines.append(f'  {edge["nodeId"]} {edge["relation"]} {edge["prerequisiteId"]}{qualifier}: {edge["reason"]}')
        lines.append('    Scope: ' + edge['scope'] + '; review: ' + edge['reviewStatus'])
    for flag in result.get('flags', []):
        lines.append('Qualification: ' + flag)
    lines.append('Omissions: ' + _json(result['omissions']))
    return '\n'.join(lines)


def main(argv=None):
    # The portable catalog includes Chinese source definitions. Windows console
    # defaults must not make a valid extraction fail while printing those names.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'validate', 'extract', 'inspect'))
    parser.add_argument('question_id', nargs='?')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--layer', choices=('CN', 'US', 'ailleo'), default='ailleo')
    parser.add_argument('--depth', type=int, default=1)
    parser.add_argument('--dependents', action='store_true')
    parser.add_argument('--max-nodes', type=int, default=DEFAULT_MAX_NODES)
    parser.add_argument('--max-chars', type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument('--json', action='store_true', dest='as_json')
    args = parser.parse_args(argv)
    try:
        if args.command == 'build':
            result = build_database(args.root)
        elif args.command == 'validate':
            result = validate_database(args.root)
        elif args.command == 'inspect':
            if not args.question_id:
                parser.error('inspect requires NODE_ID')
            import curriculum_graph
            result = {'annotations': curriculum_graph.annotations_for_node(args.question_id, args.root),
                      'neighborhood': curriculum_graph.layer_neighborhood(args.question_id, args.layer, args.root, args.depth, args.max_nodes)}
        elif not args.question_id:
            parser.error('extract requires QUESTION_ID')
        else:
            result = context_for_question(load_question(args.question_id, args.root), args.root,
                                          args.max_nodes, args.max_chars, args.depth, dependents=args.dependents, layer=args.layer)
        if args.as_json or args.command != 'extract':
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_context(result))
        return 0
    except GraphError as exc:
        parser.exit(1, f'Graph error: {exc}\n')


if __name__ == '__main__':
    main()
