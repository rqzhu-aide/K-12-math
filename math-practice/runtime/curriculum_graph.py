"""Native curriculum graphs and explicit crosswalks to the common mathematics graph.

Source placements are annotations, never inferred prerequisites or mastery evidence.
Alignment narrower means the canonical concept is narrower than the source node;
broader means the canonical concept is broader than the source node.
"""
from collections import deque
from contextlib import closing
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYERS = ('CN', 'US', 'ailleo')
DDL = '''
CREATE TABLE curriculum_layers (id TEXT PRIMARY KEY, raw_json TEXT NOT NULL);
CREATE TABLE curriculum_nodes (layer TEXT NOT NULL REFERENCES curriculum_layers(id), id TEXT NOT NULL,
 raw_json TEXT NOT NULL, PRIMARY KEY(layer,id));
CREATE TABLE curriculum_relationships (layer TEXT NOT NULL, id TEXT NOT NULL, from_id TEXT NOT NULL,
 to_id TEXT NOT NULL, relation TEXT NOT NULL, raw_json TEXT NOT NULL, PRIMARY KEY(layer,id),
 FOREIGN KEY(layer,from_id) REFERENCES curriculum_nodes(layer,id),
 FOREIGN KEY(layer,to_id) REFERENCES curriculum_nodes(layer,id));
CREATE TABLE concept_alignments (id TEXT PRIMARY KEY, node_id TEXT NOT NULL REFERENCES nodes(id),
 layer TEXT NOT NULL, source_node_id TEXT NOT NULL, relation TEXT NOT NULL, status TEXT NOT NULL,
 raw_json TEXT NOT NULL, FOREIGN KEY(layer,source_node_id) REFERENCES curriculum_nodes(layer,id));
CREATE INDEX alignments_node ON concept_alignments(node_id,layer,status);
CREATE INDEX alignments_source ON concept_alignments(layer,source_node_id,status);
'''


def _graph():
    import knowledge_graph
    return knowledge_graph


def validate_source(curricula, alignments, node_ids):
    g = _graph()
    if not isinstance(curricula, dict) or curricula.get('schemaVersion') != 1 or not isinstance(curricula.get('layers'), list):
        raise g.GraphError('curricula: expected schemaVersion 1 and layers array.')
    if not isinstance(alignments, list):
        raise g.GraphError('alignments: expected an array.')
    seen_layers, source_ids = set(), set()
    for layer in curricula['layers']:
        g._object(layer, 'curriculum layer')
        lid = layer.get('id')
        if lid not in ('CN', 'US') or lid in seen_layers:
            raise g.GraphError('Invalid or duplicate curriculum layer.')
        seen_layers.add(lid)
        for key in ('label', 'source', 'revision', 'placementMeaning'):
            if key == 'source' and isinstance(layer.get(key), dict):
                continue
            g._text(layer.get(key), f'{lid}.{key}')
        if not isinstance(layer.get('nodes'), list) or not isinstance(layer.get('relationships'), list):
            raise g.GraphError(f'{lid}: expected nodes and relationships arrays.')
        ids = set()
        for node in layer['nodes']:
            g._object(node, f'{lid}.node')
            for key in ('id', 'label', 'description'):
                g._text(node.get(key), f'{lid}.node.{key}')
            g._object(node.get('placement'), f'{lid}.{node["id"]}.placement')
            if node['id'] in ids:
                raise g.GraphError(f'{lid}: duplicate source node ID.')
            ids.add(node['id'])
            source_ids.add((lid, node['id']))
        edge_ids = set()
        for edge in layer['relationships']:
            g._object(edge, f'{lid}.relationship')
            g._text(edge.get('id'), f'{lid}.relationship.id')
            if edge['id'] in edge_ids or edge.get('fromId') not in ids or edge.get('toId') not in ids:
                raise g.GraphError(f'{lid}: duplicate edge or unknown source endpoint.')
            edge_ids.add(edge['id'])
            if edge.get('relation') not in ('prerequisite', 'related', 'contains', 'supports', 'coherence_progression') or edge.get('status', 'accepted') not in g.STATUSES:
                raise g.GraphError(f'{lid}: invalid native relationship.')
        # Only enforce acyclicity when the source explicitly claims a DAG.
        if layer.get('prerequisiteDAG') is True:
            g._requires_cycles([{'id': e['id'], 'nodeId': e['fromId'], 'prerequisiteId': e['toId'],
                'relation': 'requires', 'status': e.get('status', 'accepted')} for e in layer['relationships']
                if e['relation'] == 'prerequisite'])
    alignment_ids, signatures = set(), set()
    for a in alignments:
        g._object(a, 'alignment')
        g._text(a.get('id'), 'alignment.id')
        signature = (a.get('nodeId'), a.get('layer'), a.get('sourceNodeId'), a.get('relation'))
        if a['id'] in alignment_ids or signature in signatures:
            raise g.GraphError('Duplicate alignment.')
        alignment_ids.add(a['id'])
        signatures.add(signature)
        if a.get('nodeId') not in node_ids or (a.get('layer'), a.get('sourceNodeId')) not in source_ids:
            raise g.GraphError(f'{a["id"]}: unknown crosswalk endpoint or layer.')
        if a.get('relation') not in ('exact', 'narrower', 'broader', 'partial') or a.get('status') not in g.STATUSES:
            raise g.GraphError(f'{a["id"]}: invalid alignment relation/status.')
        for key in ('reason', 'reviewStatus'):
            g._text(a.get(key), f'{a["id"]}.{key}')


def load_optional(directory, node_ids):
    directory = Path(directory)
    curricula = json.loads((directory / 'curricula.json').read_text(encoding='utf-8-sig')) if (directory / 'curricula.json').is_file() else {'schemaVersion': 1, 'layers': []}
    alignments = json.loads((directory / 'alignments.json').read_text(encoding='utf-8-sig')) if (directory / 'alignments.json').is_file() else []
    if isinstance(alignments, dict):
        alignments = alignments.get('alignments')
    validate_source(curricula, alignments, node_ids)
    return curricula, alignments


def insert_source(connection, source):
    g = _graph()
    for layer in source['curricula']['layers']:
        metadata = {k: v for k, v in layer.items() if k not in ('nodes', 'relationships')}
        connection.execute('INSERT INTO curriculum_layers VALUES (?,?)', (layer['id'], g._json(metadata)))
        for n in layer['nodes']:
            connection.execute('INSERT INTO curriculum_nodes VALUES (?,?,?)', (layer['id'], n['id'], g._json(n)))
        for e in layer['relationships']:
            connection.execute('INSERT INTO curriculum_relationships VALUES (?,?,?,?,?,?)',
                (layer['id'], e['id'], e['fromId'], e['toId'], e['relation'], g._json(e)))
    for a in source['alignments']:
        connection.execute('INSERT INTO concept_alignments VALUES (?,?,?,?,?,?,?)',
            (a['id'], a['nodeId'], a['layer'], a['sourceNodeId'], a['relation'], a['status'], g._json(a)))


def source_from_db(connection):
    layers = []
    for row in connection.execute('SELECT id,raw_json FROM curriculum_layers ORDER BY id'):
        layer = json.loads(row['raw_json'] if hasattr(row, 'keys') else row[1])
        lid = layer['id']
        layer['nodes'] = [json.loads(r[0]) for r in connection.execute('SELECT raw_json FROM curriculum_nodes WHERE layer=? ORDER BY id', (lid,))]
        layer['relationships'] = [json.loads(r[0]) for r in connection.execute('SELECT raw_json FROM curriculum_relationships WHERE layer=? ORDER BY id', (lid,))]
        layers.append(layer)
    return {'schemaVersion': 1, 'layers': layers}, [json.loads(r[0]) for r in connection.execute('SELECT raw_json FROM concept_alignments ORDER BY id')]


def validate_index(connection, source):
    """Compare normalized columns and rows to a fresh index of retained source."""
    import sqlite3
    with closing(sqlite3.connect(':memory:')) as expected:
        expected.executescript(DDL)
        insert_source(expected, source)
        for table in ('curriculum_layers', 'curriculum_nodes', 'curriculum_relationships', 'concept_alignments'):
            a = sorted([tuple(r) for r in connection.execute(f'SELECT * FROM {table}')])
            b = sorted(expected.execute(f'SELECT * FROM {table}').fetchall())
            if a != b:
                raise _graph().GraphError(f'{table}: curriculum index differs from retained source.')


def _connection(root):
    g = _graph()
    return closing(g._connect_readonly(g._db_path(root, None)))


def _layer(layer):
    if layer not in LAYERS:
        raise _graph().GraphError(f'Unknown curriculum layer {layer}.')


def validate_selection(layer, node_id, root=ROOT):
    """Resolve only an installed identifier, never a client-supplied definition."""
    _layer(layer)
    if node_id is None or node_id == '':
        return None
    if not isinstance(node_id, str) or not node_id.strip() or len(node_id) > 200:
        raise _graph().GraphError('Choose a valid curriculum concept or standard.')
    with _connection(root) as c:
        if layer == 'ailleo':
            row = c.execute('SELECT 1 FROM nodes WHERE id=?', (node_id,)).fetchone()
        else:
            row = c.execute('SELECT 1 FROM curriculum_nodes WHERE layer=? AND id=?', (layer, node_id)).fetchone()
        if row is None:
            raise _graph().GraphError('Unknown selected curriculum concept or standard.')
    return node_id


def matching_selection(layer, node_id, canonical_ids, root=ROOT):
    """Accepted overlap with bound assessed/route concepts; no match is explicit."""
    validate_selection(layer, node_id, root)
    if layer == 'ailleo':
        return [node_id] if node_id in canonical_ids else []
    with _connection(root) as c:
        rows = c.execute("SELECT DISTINCT node_id FROM concept_alignments WHERE layer=? AND source_node_id=? AND status='accepted' ORDER BY node_id", (layer, node_id))
        return [r[0] for r in rows if r[0] in canonical_ids]


def layer_catalog(root=ROOT):
    with _connection(root) as c:
        rows = [json.loads(r[0]) for r in c.execute('SELECT raw_json FROM curriculum_layers ORDER BY id')]
        installed = {r['id'] for r in rows}
        rows += [{'id': lid, 'label': lid, 'status': 'unavailable'} for lid in ('CN', 'US') if lid not in installed]
        rows.append({'id': 'ailleo', 'label': 'ailleo', 'placementMeaning': 'Gradeless mathematical dependencies; no national curriculum placement.', 'status': 'available'})
        return {'layers': rows}


def _alignments(c, node_id, layer, accepted=False):
    return [json.loads(r[0]) for r in c.execute('SELECT raw_json FROM concept_alignments WHERE node_id=? AND layer=?' + (" AND status='accepted'" if accepted else '') + ' ORDER BY id', (node_id, layer))]


def _concept(node):
    return {k: node.get(k) for k in ('id', 'name', 'nameZh', 'description', 'criteria', 'kind', 'reviewStatus')}


def _math_edge(edge):
    return {k: edge.get(k) for k in ('id', 'nodeId', 'prerequisiteId', 'relation', 'scope', 'reason', 'reviewStatus')}


def _status(alignments):
    accepted = [a for a in alignments if a['status'] == 'accepted']
    if not accepted:
        return 'unmapped'
    return 'mapped' if all(a['relation'] == 'exact' for a in accepted) else 'partial'


def annotations_for_node(node_id, root=ROOT):
    with _connection(root) as c:
        row = c.execute('SELECT name FROM nodes WHERE id=?', (node_id,)).fetchone()
        if row is None:
            raise _graph().GraphError(f'Unknown canonical node {node_id}.')
        result = {'id': node_id, 'name': row[0]}
        for lid in ('CN', 'US'):
            alignments = _alignments(c, node_id, lid)
            for a in alignments:
                a['sourceNode'] = json.loads(c.execute('SELECT raw_json FROM curriculum_nodes WHERE layer=? AND id=?', (lid, a['sourceNodeId'])).fetchone()[0])
            source_ids = {a['sourceNodeId'] for a in alignments if a['status'] == 'accepted'}
            connections = [json.loads(r[0]) for r in c.execute('SELECT raw_json FROM curriculum_relationships WHERE layer=? ORDER BY id', (lid,))]
            connections = [e for e in connections if e.get('status', 'accepted') == 'accepted' and (e['fromId'] in source_ids or e['toId'] in source_ids)]
            metadata = c.execute('SELECT raw_json FROM curriculum_layers WHERE id=?', (lid,)).fetchone()
            result[lid] = {'status': _status(alignments), 'alignments': alignments, 'connections': connections,
                           'metadata': json.loads(metadata[0]) if metadata else None}
        result['ailleo'] = {'status': 'mapped', 'placement': None, 'meaning': 'Gradeless mathematical graph.',
                            'connections': [_math_edge(json.loads(r[0])) for r in c.execute(
                                "SELECT raw_json FROM relationships WHERE status='accepted' AND (node_id=? OR prerequisite_id=?) ORDER BY id", (node_id, node_id))]}
        return result


def layer_neighborhood(node_id, layer, root=ROOT, depth=1, limit=16, *, source_node_id=None):
    _layer(layer)
    if not isinstance(depth, int) or not 0 <= depth <= 20 or not isinstance(limit, int) or limit < 1:
        raise _graph().GraphError('Neighborhood requires depth 0..20 and positive limit.')
    with _connection(root) as c:
        if c.execute('SELECT 1 FROM nodes WHERE id=?', (node_id,)).fetchone() is None:
            raise _graph().GraphError(f'Unknown canonical node {node_id}.')
        if layer == 'ailleo':
            seeds, alignments, status = [node_id], [], 'mapped'
            all_nodes = {r[0]: _concept(json.loads(r[1])) for r in c.execute('SELECT id,raw_json FROM nodes')}
            edges = [dict(_math_edge(json.loads(r[0])), layer='ailleo') for r in c.execute("SELECT raw_json FROM relationships WHERE status='accepted' ORDER BY id")]
            endpoints = lambda e: (e['nodeId'], e['prerequisiteId'])
        else:
            alignments = _alignments(c, node_id, layer, accepted=True)
            if source_node_id is not None:
                alignments = [a for a in alignments if a['sourceNodeId'] == source_node_id]
            seeds = list(dict.fromkeys(a['sourceNodeId'] for a in alignments))
            status = _status(alignments)
            all_nodes = {r[0]: json.loads(r[1]) for r in c.execute('SELECT id,raw_json FROM curriculum_nodes WHERE layer=?', (layer,))}
            edges = [json.loads(r[0]) for r in c.execute('SELECT raw_json FROM curriculum_relationships WHERE layer=? ORDER BY id', (layer,))]
            edges = [e for e in edges if e.get('status', 'accepted') == 'accepted']
            endpoints = lambda e: (e['fromId'], e['toId'])
        visited, queue, omitted = set(), deque((s, 0) for s in seeds), set()
        while queue:
            current, distance = queue.popleft()
            if current in visited:
                continue
            if len(visited) >= limit:
                omitted.add(current)
                continue
            visited.add(current)
            if distance < depth:
                for e in edges:
                    a, b = endpoints(e)
                    if current in (a, b):
                        queue.append((b if current == a else a, distance + 1))
        return {'nodeId': node_id, 'layer': layer, 'status': status,
                'nodes': [all_nodes[n] for n in sorted(visited)],
                'relationships': [e for e in edges if set(endpoints(e)) <= visited],
                'alignments': [a for a in alignments if a['sourceNodeId'] in visited],
                'truncated': bool(omitted), 'meaning': 'Native source edges only. Crosswalks do not create mathematical prerequisites.'}


def _practice_distance(mapping, target_ids):
    assessed = set(mapping['assessedIds'])
    direct = bool(assessed & target_ids)
    routes = mapping['routes'] if direct else [r for r in mapping['routes'] if target_ids & set(r['nodeIds'])]
    choices = [assessed | set(r['nodeIds']) for r in routes] or [assessed]
    return min(len(nodes - target_ids) for nodes in choices)


def _practice_rank(candidate):
    return (not candidate['assessed'], candidate['additionalConceptCount'], candidate['questionId'])


def practice_candidates(node_id, layer, root=ROOT, limit=16, offset=0):
    _layer(layer)
    if not isinstance(limit, int) or limit < 1:
        raise _graph().GraphError('Practice limit must be positive.')
    if type(offset) is not int or offset < 0:
        raise _graph().GraphError('Practice offset must be a nonnegative integer.')
    with _connection(root) as c:
        if c.execute('SELECT 1 FROM nodes WHERE id=?', (node_id,)).fetchone() is None:
            raise _graph().GraphError(f'Unknown canonical node {node_id}.')
        alignments = [] if layer == 'ailleo' else _alignments(c, node_id, layer, accepted=True)
        status = 'mapped' if layer == 'ailleo' else _status(alignments)
        candidates = []
        if status != 'unmapped':
            rows = c.execute("SELECT DISTINCT q.question_id,q.raw_json FROM questions q LEFT JOIN question_nodes n ON q.question_id=n.question_id LEFT JOIN route_nodes r ON q.question_id=r.question_id WHERE q.status='mapped' AND ((n.node_id=? AND n.role='assessed') OR r.node_id=?) ORDER BY q.question_id", (node_id, node_id))
            for row in rows:
                mapping = json.loads(row[1])
                candidates.append({'questionId': row[0], 'bank': mapping['bank'], 'coverage': 'canonical_concept_only' if layer == 'ailleo' else ('aligned_concept_only' if status == 'mapped' else 'partial'), 'reviewStatus': mapping['reviewStatus'], 'answerCheck': mapping['answerCheck'], 'flags': mapping['flags'], 'routes': [r for r in mapping['routes'] if node_id in r['nodeIds']], 'assessed': node_id in mapping['assessedIds'], 'additionalConceptCount': _practice_distance(mapping, {node_id})})
        candidates.sort(key=_practice_rank)
        return {'nodeId': node_id, 'layer': layer, 'status': status, 'alignments': alignments,
                'candidates': candidates[offset:offset + limit], 'total': len(candidates),
                'nextOffset': offset + limit if offset + limit < len(candidates) else None,
                'meaning': 'Reviewed content-bound concept practice; no claim of complete source-standard coverage or learner mastery.'}


def browse_layer(layer, root=ROOT):
    """Return a whole native layer, including source nodes without any crosswalk."""
    _layer(layer)
    with _connection(root) as c:
        if layer == 'ailleo':
            nodes = [_concept(json.loads(r[0])) for r in c.execute('SELECT raw_json FROM nodes ORDER BY id')]
            relationships = [_math_edge(json.loads(r[0])) for r in c.execute("SELECT raw_json FROM relationships WHERE status='accepted' ORDER BY id")]
            return {'layer': layer, 'status': 'available', 'nodes': nodes, 'relationships': relationships, 'alignments': []}
        row = c.execute('SELECT raw_json FROM curriculum_layers WHERE id=?', (layer,)).fetchone()
        return {'layer': layer, 'status': 'available' if row else 'unavailable',
                'metadata': json.loads(row[0]) if row else None,
                'nodes': [json.loads(r[0]) for r in c.execute('SELECT raw_json FROM curriculum_nodes WHERE layer=? ORDER BY id', (layer,))],
                'relationships': [json.loads(r[0]) for r in c.execute('SELECT raw_json FROM curriculum_relationships WHERE layer=? ORDER BY id', (layer,)) if json.loads(r[0]).get('status', 'accepted') == 'accepted'],
                'alignments': [json.loads(r[0]) for r in c.execute("SELECT raw_json FROM concept_alignments WHERE layer=? AND status='accepted' ORDER BY id", (layer,))]}


def practice_for_source(source_node_id, layer, root=ROOT, limit=30, offset=0):
    """Keep a native standard visible even when no reviewed practice crosswalk exists."""
    _layer(layer)
    if layer == 'ailleo':
        return practice_candidates(source_node_id, layer, root, limit, offset)
    if not isinstance(limit, int) or limit < 1:
        raise _graph().GraphError('Practice limit must be positive.')
    if type(offset) is not int or offset < 0:
        raise _graph().GraphError('Practice offset must be a nonnegative integer.')
    with _connection(root) as c:
        row = c.execute('SELECT raw_json FROM curriculum_nodes WHERE layer=? AND id=?', (layer, source_node_id)).fetchone()
        if row is None:
            raise _graph().GraphError(f'Unknown source node {layer}:{source_node_id}.')
        source_node = json.loads(row[0])
        alignments = [json.loads(r[0]) for r in c.execute("SELECT raw_json FROM concept_alignments WHERE layer=? AND source_node_id=? AND status='accepted' ORDER BY id", (layer, source_node_id))]
        question_count = c.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
    candidates = {}
    for alignment in alignments:
        practice = practice_candidates(alignment['nodeId'], layer, root, max(1, question_count))
        for candidate in practice['candidates']:
            item = candidates.setdefault(candidate['questionId'], {**candidate, 'canonicalNodeIds': [], 'alignmentIds': [], 'coverage': 'aligned_concept_only'})
            item['routes'] = list({r['id']: r for r in item['routes'] + candidate['routes']}.values())
            item['assessed'] = item['assessed'] or candidate['assessed']
            item['canonicalNodeIds'].append(alignment['nodeId'])
            item['alignmentIds'].append(alignment['id'])
            if alignment['relation'] != 'exact':
                item['coverage'] = 'partial'
    if candidates:
        with _connection(root) as c:
            for item in candidates.values():
                mapping = json.loads(c.execute('SELECT raw_json FROM questions WHERE question_id=?', (item['questionId'],)).fetchone()[0])
                item['additionalConceptCount'] = _practice_distance(mapping, set(item['canonicalNodeIds']))
    ordered = sorted(candidates.values(), key=_practice_rank)
    return {'sourceNodeId': source_node_id, 'layer': layer, 'label': source_node['label'],
            'sourceNode': source_node, 'status': _status(alignments), 'alignments': alignments,
            'canonicalNodeIds': sorted({a['nodeId'] for a in alignments}),
            'candidates': ordered[offset:offset + limit], 'total': len(ordered),
            'nextOffset': offset + limit if offset + limit < len(ordered) else None,
            'meaning': 'Practice covers aligned canonical concepts, with no claim of complete standard coverage or mastery.'}


def compact_neighborhood(node_id, layer, root=ROOT, depth=1, limit=8, *, source_node_id=None):
    """Small native-only teaching supplement; preserve source identity and crosswalk scope."""
    result = layer_neighborhood(node_id, layer, root, depth, limit, source_node_id=source_node_id)
    seed_ids = {a['sourceNodeId'] for a in result['alignments']}
    result['nodes'] = [{k: n.get(k) for k in ('id', 'label', 'placement')} | {'description': n.get('description', '')[:320]}
                       for n in sorted(result['nodes'], key=lambda n: (n['id'] not in seed_ids, n['id']))]
    result['relationships'] = [{k: e.get(k) for k in ('id', 'fromId', 'toId', 'relation', 'directed')}
                               for e in result['relationships']]
    result['alignments'] = [{k: a.get(k) for k in ('id', 'nodeId', 'sourceNodeId', 'relation', 'status', 'reviewStatus')}
                            for a in result['alignments']]
    result['omissions'] = {'nodes': 0, 'relationships': 0}
    return result


def compact_tutor_prerequisites(node_id, layer, root=ROOT, depth=1, limit=8, *, source_node_id=None, existing_node_ids=()):
    """Mapped native concepts and their direct foundations, without browse neighbors.

    Both native sources store dependent -> foundation. A supports edge is helpful
    preparation, not a hard prerequisite. Crosswalks select roots, never edges.
    """
    _layer(layer)
    if layer == 'ailleo':
        raise _graph().GraphError('Native prerequisite context requires CN or US.')
    if not isinstance(depth, int) or not 0 <= depth <= 1 or not isinstance(limit, int) or limit < 1:
        raise _graph().GraphError('Tutor prerequisites require depth 0..1 and a positive limit.')
    with _connection(root) as c:
        if c.execute('SELECT 1 FROM nodes WHERE id=?', (node_id,)).fetchone() is None:
            raise _graph().GraphError(f'Unknown canonical node {node_id}.')
        alignments = _alignments(c, node_id, layer, accepted=True)
        if source_node_id is not None:
            alignments = [a for a in alignments if a['sourceNodeId'] == source_node_id]
        seeds = list(dict.fromkeys(a['sourceNodeId'] for a in alignments))
        seed_ids = set(seeds)
        edges = []
        if depth:
            for row in c.execute('SELECT raw_json FROM curriculum_relationships WHERE layer=? ORDER BY id', (layer,)):
                edge = json.loads(row[0])
                if (edge['fromId'] in seed_ids and edge['relation'] in ('prerequisite', 'supports')
                        and edge.get('directed', True) and edge.get('status', 'accepted') == 'accepted'):
                    edges.append(edge)
        edges.sort(key=lambda e: (e['relation'] != 'prerequisite', e['id']))
        candidates = list(dict.fromkeys(seeds + [e['toId'] for e in edges]))
        # A shared foundation can appear in several question-route neighborhoods.
        # Count it once in the shared budget while retaining each local edge.
        allocated = set(existing_node_ids)
        included = []
        for native_id in seeds:
            if native_id in allocated or len(allocated) < limit:
                included.append(native_id)
                allocated.add(native_id)
        for edge in edges:
            native_id = edge['toId']
            if (edge['fromId'] in included and native_id not in included
                    and (native_id in allocated or len(allocated) < limit)):
                included.append(native_id)
                allocated.add(native_id)
        included_ids = set(included)
        nodes = []
        for native_id in included:
            node = json.loads(c.execute('SELECT raw_json FROM curriculum_nodes WHERE layer=? AND id=?',
                                        (layer, native_id)).fetchone()[0])
            nodes.append({k: node.get(k) for k in ('id', 'label', 'placement', 'description', 'criteria')})
        kept_edges = [e for e in edges if {e['fromId'], e['toId']} <= included_ids]
        omissions = {'nodes': len(candidates) - len(included), 'relationships': len(edges) - len(kept_edges)}
        return {'nodeId': node_id, 'layer': layer, 'status': _status(alignments), 'depth': depth,
                'nodes': nodes,
                'relationships': [{k: e.get(k) for k in ('id', 'fromId', 'toId', 'relation', 'directed', 'directionMeaning')}
                                  for e in kept_edges],
                'alignments': [{k: a.get(k) for k in ('id', 'nodeId', 'sourceNodeId', 'relation', 'status', 'reviewStatus')}
                               for a in alignments if a['sourceNodeId'] in included_ids],
                'truncated': any(omissions.values()), 'omissions': omissions,
                'meaning': 'Native concept to foundation: prerequisite is for that concept; supports is helpful preparation. Another solution may use neither. Crosswalks add no prerequisites.'}
