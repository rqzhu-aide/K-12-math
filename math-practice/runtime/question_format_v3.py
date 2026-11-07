"""Read the portable v3 record into the existing in-memory practice model.

The source record is never rewritten by normalization. Methods retain their own
text, direct concepts and credit; a graph-only method stays graph-only.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from layout import database_root
import re

ROOT = Path(__file__).resolve().parents[2]


class QuestionFormatError(ValueError):
    pass


class NormalizedQuestion(dict):
    """An in-memory view, never an accepted on-disk question representation."""


class SourceIndex(dict):
    """A parsed, validated bank index retained in a bounded revision cache."""


def is_v3(record):
    return isinstance(record, dict) and (record.get('schemaVersion') == '3.0' or isinstance(record, NormalizedQuestion))


def raw_question(record):
    return record.get('_QuestionV3', record)


def _text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise QuestionFormatError(where + ' must be nonempty text.')


def _strings(value, where, *, nonempty=False):
    if (not isinstance(value, list) or (nonempty and not value)
            or any(not isinstance(x, str) or not x.strip() for x in value) or len(value) != len(set(value))):
        raise QuestionFormatError(where + ' must be a list of distinct nonempty strings.')


def validate_question(record):
    """Enforce the portable shape and sibling references without a new runtime dependency."""
    if not isinstance(record, dict):
        raise QuestionFormatError('A question must be an object.')
    required = {'schemaVersion','id','bank','language','question','answer','classification','assessedNodeIds','solutions','sourceRef'}
    if set(record) != required or record.get('schemaVersion') != '3.0' or record.get('language') != 'en':
        raise QuestionFormatError('Use the question format 3.0 fields and language en.')
    for key in ('id','bank','sourceRef'):
        _text(record[key], key)
    if record['bank'] not in ('amc','cn-math'):
        if (not re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*', record['bank']) or len(record['bank']) > 48
                or not record['id'].startswith(record['bank']+'__')):
            raise QuestionFormatError('A custom bank needs a safe bank ID and matching question prefix.')
    if not re.fullmatch(r'[A-Za-z0-9_]{1,120}', record['id']):
        raise QuestionFormatError('Question id must use letters, digits and underscores, up to 120 characters.')
    question, answer, classification = record['question'], record['answer'], record['classification']
    if not isinstance(question, dict) or not {'prompt'} <= set(question) <= {'prompt','choices'}:
        raise QuestionFormatError('question needs prompt and optional choices.')
    _text(question['prompt'], 'question.prompt')
    if not isinstance(answer, dict) or not {'type'} <= set(answer) <= {'type','accepted','rubric','rejected','unordered','form','gradingNote'}:
        raise QuestionFormatError('answer contains unsupported fields.')
    kind = answer['type']
    if kind not in ('choice','multiSelect','numeric','short','self'):
        raise QuestionFormatError('Unsupported answer type.')
    choices = question.get('choices')
    if kind in ('choice','multiSelect'):
        if not isinstance(choices, list) or len(choices) < 2:
            raise QuestionFormatError('A choice response needs at least two ordered choices.')
        ids = []
        for choice in choices:
            if not isinstance(choice, dict) or set(choice) != {'id','content'}:
                raise QuestionFormatError('Each choice needs id and content.')
            _text(choice['id'], 'choice.id')
            _text(choice['content'], 'choice.content')
            ids.append(choice['id'])
        if len(ids) != len(set(ids)):
            raise QuestionFormatError('Choice IDs must be distinct.')
    elif choices is not None:
        raise QuestionFormatError('Only choice and multiSelect questions have choices.')
    if kind == 'self':
        _text(answer.get('rubric'), 'answer.rubric')
        if 'accepted' in answer:
            raise QuestionFormatError('A self-assessed response uses a rubric instead of accepted answers.')
    else:
        accepted = answer.get('accepted')
        if not isinstance(accepted, list) or not accepted or 'rubric' in answer:
            raise QuestionFormatError('An automatically checked answer needs accepted complete responses.')
        seen = set()
        for response in accepted:
            if kind == 'multiSelect':
                _strings(response, 'a complete multiSelect response', nonempty=True)
                if not set(response) <= set(ids):
                    raise QuestionFormatError('An accepted multiSelect response names an unknown choice.')
                identity = tuple(sorted(response))
            else:
                _text(response, 'an accepted complete response')
                if kind == 'choice' and response not in ids:
                    raise QuestionFormatError('An accepted response names an unknown choice.')
                identity = response
            if identity in seen:
                raise QuestionFormatError('Accepted complete responses must be distinct.')
            seen.add(identity)
        if kind == 'numeric':
            from question_answers import numeric_list
            try:
                for response in accepted:
                    numeric_list(response)
            except (ValueError, ZeroDivisionError):
                raise QuestionFormatError('Numeric accepted responses must be numbers, fractions or complete comma-separated lists.') from None
    if 'rejected' in answer:
        _strings(answer['rejected'], 'answer.rejected')
        if kind != 'multiSelect' and set(answer['rejected']) & set(answer.get('accepted', [])):
            raise QuestionFormatError('A response cannot be both accepted and rejected.')
    if 'unordered' in answer and (kind != 'numeric' or answer['unordered'] is not True):
        raise QuestionFormatError('unordered:true is supported only for numeric responses.')
    if answer.get('form') not in (None,'decimal','standard-monomial','ordered-list'):
        raise QuestionFormatError('Unsupported answer form.')
    if 'gradingNote' in answer:
        _text(answer['gradingNote'], 'answer.gradingNote')
    allowed = {'area','domainIds','topicIds','skillIds','grade','level','unit','difficulty'}
    if not isinstance(classification, dict) or set(classification) - allowed:
        raise QuestionFormatError('Unsupported classification fields.')
    for key, value in classification.items():
        if key.endswith('Ids'):
            _strings(value, 'classification.'+key)
        elif key == 'grade':
            if type(value) is not int or value < 0:
                raise QuestionFormatError('classification.grade must be a nonnegative integer.')
        else:
            _text(value, 'classification.'+key)
    _strings(record['assessedNodeIds'], 'assessedNodeIds')
    if not isinstance(record['solutions'], list):
        raise QuestionFormatError('solutions must be a list.')
    methods = set()
    for method in record['solutions']:
        if (not isinstance(method, dict) or not {'id','title'} <= set(method) <= {'id','title','explanation','directNodeIds','sourceRef'}
                or not {'explanation','directNodeIds'} & set(method)):
            raise QuestionFormatError('Each solution needs id/title and explanation, directNodeIds, or both.')
        for key in ('id','title','explanation','sourceRef'):
            if key in method:
                _text(method[key], 'solution.'+key)
        if method['id'] in methods:
            raise QuestionFormatError('Solution IDs must be distinct.')
        methods.add(method['id'])
        if 'directNodeIds' in method:
            _strings(method['directNodeIds'], 'solution.directNodeIds', nonempty=True)


def load_source_index(bank_root):
    path = (Path(bank_root) / 'source-index.json').resolve()
    try:
        stat = path.stat()
        return _cached_source_index(str(path), stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError) as exc:
        raise QuestionFormatError('Cannot read bank source-index.json: '+str(exc)) from None


@lru_cache(maxsize=8)
def _cached_source_index(path, modified_ns, size):
    index = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate_source_index(index)
    return SourceIndex(index)


def validate_source_index(index):
    if (not isinstance(index, dict) or index.get('schemaVersion') != '3.0'
            or not isinstance(index.get('sources'), dict) or not isinstance(index.get('bank'), str)):
        raise QuestionFormatError('source-index.json needs schemaVersion 3.0, bank and a sources object.')
    for key, entry in index['sources'].items():
        _text(key, 'a source-index key')
        if not isinstance(entry, dict):
            raise QuestionFormatError('Each source-index entry must be an object.')
        for field in ('meta','position','topicLabels','provenance'):
            if field in entry and not isinstance(entry[field], dict):
                raise QuestionFormatError('Source '+field+' must be an object.')
        if 'assets' in entry and (not isinstance(entry['assets'], list) or any(not isinstance(a, dict) for a in entry['assets'])):
            raise QuestionFormatError('Source assets must be a list of objects.')


def _evidence_summary(value):
    if isinstance(value, list):
        return [_evidence_summary(item) for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return {k:deepcopy(value[k]) for k in ('path','sha256','label','kind') if k in value}
    return None


def portable_source_files(bank_root):
    """Retain only explicitly indexed, hash-bound archived provenance on import."""
    bank_root = Path(bank_root).resolve()
    index = load_source_index(bank_root)
    files = {'source-index.json':(bank_root/'source-index.json').read_bytes()}
    def visit(value):
        if isinstance(value, dict):
            relative = value.get('path')
            if isinstance(relative, str) and relative.startswith('archive/') and 'sha256' in value:
                path = (bank_root/relative).resolve()
                if not path.is_relative_to(bank_root/'archive'):
                    raise QuestionFormatError('An archived source reference leaves its bank.')
                try:
                    data = path.read_bytes()
                except OSError:
                    raise QuestionFormatError('An indexed archived source is missing: '+relative) from None
                if hashlib.sha256(data).hexdigest() != value['sha256']:
                    raise QuestionFormatError('An indexed archived source hash differs: '+relative)
                files[relative] = data
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(index)
    return files


def normalize_question(record, *, root=ROOT, bank_root=None, source_index=None):
    """Return the legacy runtime view of v3, or the original v2 object unchanged."""
    if isinstance(record, NormalizedQuestion):
        return record
    if isinstance(record, dict) and ('_QuestionV3' in record or record.get('SchemaVersion') == '3.0'):
        raise QuestionFormatError('A saved v3 question must use the portable lowercase fields, without runtime markers.')
    if not is_v3(record):
        return record
    validate_question(record)
    if bank_root is None:
        bank_root = (database_root(root) / {'amc':'amc-bank','cn-math':'cn-math-bank'}[record['bank']]
                     if record['bank'] in ('amc','cn-math') else Path(root) / 'custom-banks' / record['bank'])
        if record['bank'] not in ('amc','cn-math') and not (bank_root/'bank.json').is_file():
            raise QuestionFormatError('The custom question bank is not installed.')
    index = source_index if source_index is not None else load_source_index(bank_root)
    if not isinstance(index, SourceIndex):
        validate_source_index(index)
    if index.get('bank') != record['bank']:
        raise QuestionFormatError('The question bank differs from source-index.json.')
    sources = index.get('sources', {})
    def resolved(key):
        value = sources.get(key)
        if not isinstance(value, dict):
            raise QuestionFormatError('Unresolved sourceRef: '+key)
        return deepcopy(value)
    source = resolved(record['sourceRef'])
    meta = deepcopy(source.get('meta', {}))
    if not isinstance(meta, dict):
        raise QuestionFormatError('Question source metadata must be an object.')
    position = source.get('position', {})
    classification = record['classification']
    answer = record['answer']
    methods = []
    for method in record['solutions']:
        method_source = resolved(method.get('sourceRef', record['sourceRef']))
        provenance = {k:deepcopy(v) for k,v in method_source.get('provenance', {}).items()
            if k in ('source','reviewStatus','sourceURL','sourceRevision','attribution','license','licenseURL','officialSolution','evidence','teacherReviewed','contribution','reviewMeaning')}
        provenance.setdefault('source', method_source.get('label', 'Bank-provided solution; source not specified'))
        provenance.setdefault('reviewStatus', 'Review status not specified')
        provenance['sourceRef'] = method.get('sourceRef', record['sourceRef'])
        for key in ('sourceURL','license','licenseURL','evidence','officialSolution'):
            if key in method_source and key not in provenance:
                provenance[key] = deepcopy(method_source[key])
        if 'evidence' in provenance:
            provenance['evidence'] = _evidence_summary(provenance['evidence'])
        methods.append({'id':method['id'], 'label':method['title'],
            **{k:deepcopy(method[k]) for k in ('explanation','directNodeIds') if k in method},
            **({'legacyRouteId':method_source['legacyRouteId']} if method_source.get('legacyRouteId') else {}),
            'provenance':provenance})
    choices = {c['id']:c['content'] for c in record['question'].get('choices', [])}
    written = [m for m in methods if m.get('explanation')]
    topic_ids = classification.get('topicIds', [])
    labels = source.get('topicLabels', {})
    topic_id = topic_ids[0] if topic_ids else position.get('batch')
    assets = deepcopy(meta.get('FigureSources', {}))
    for asset in source.get('assets', []):
        if isinstance(asset, dict) and isinstance(asset.get('path'), str):
            assets.setdefault(asset['path'], {}).update({k:deepcopy(v) for k,v in asset.items() if k != 'path'})
    meta['FigureSources'] = assets
    summary = {k:deepcopy(source[k]) for k in ('kind','label','attribution','license','licenseURL','sourceURL','revision','position') if k in source}
    if meta:
        summary.setdefault('label', meta.get('Attribution', source.get('label','')))
        for key, original in (('attribution','Attribution'),('license','License'),('licenseURL','LicenseURL'),('sourceURL','SourceURL'),('revision','SourceRevision')):
            if meta.get(original):
                summary.setdefault(key, meta[original])
    result = NormalizedQuestion({'ID':record['id'], 'Bank':record['bank'], 'SchemaVersion':'3.0', 'Language':record['language'],
        'Question':record['question']['prompt'], 'Choices':choices, 'Choice Order':list(choices),
        'ResponseType':answer['type'], 'Correct Answer':deepcopy(answer.get('accepted', [''])[0]),
        'Accepted Responses':deepcopy(answer.get('accepted', [])), 'Accepted Answers':deepcopy(answer.get('accepted', [])[1:]),
        'Rejected Answers':deepcopy(answer.get('rejected', [])), 'Unordered Answers':answer.get('unordered', False),
        'Solution':written[0]['explanation'] if written else '', 'SolutionMethods':methods, 'SourceInfo':summary,
        'SourceRef':record['sourceRef'], 'Meta':meta, '_QuestionV3':deepcopy(record),
        'Question Type':'mixed' if '[Figure ' in record['question']['prompt'] else 'text',
        'Choices Type':'figure' if choices and all('[Figure ' in v for v in choices.values()) else 'text',
        'domain':deepcopy(classification.get('domainIds', [])), 'skill':deepcopy(classification.get('skillIds', []))})
    for source_key, target in (('area','Area'),('grade','Grade'),('level','Level'),('unit','CurriculumUnit'),('difficulty','Difficulty')):
        if source_key in classification:
            result[target] = classification[source_key]
    for source_key, target in (('year','Year'),('batch','Batch'),('number','Number')):
        if source_key in position:
            result[target] = position[source_key]
    if topic_id:
        label = labels.get(topic_id)
        legacy = labels.get('Topic', {})
        if not isinstance(label, str) and isinstance(legacy, dict) and legacy.get('id') == topic_id:
            label = legacy.get('label')
        result['Topic'] = {'id':topic_id, 'label':label if isinstance(label, str) and label.strip() else topic_id}
        result.setdefault('Batch', topic_id)
    if 'form' in answer:
        result['Answer Form'] = answer['form']
    if 'rubric' in answer:
        result['Answer Rubric'] = answer['rubric']
    if 'gradingNote' in answer:
        result.update(GradingStatus='disputed', GradingNote=answer['gradingNote'])
    if source.get('sourceContentNote'):
        result['Source Content Note'] = source['sourceContentNote']
    return result


def fingerprint_payload(question):
    raw = raw_question(question)
    result = {k:deepcopy(raw[k]) for k in ('schemaVersion','id','bank','language','question','answer','classification','assessedNodeIds','solutions')}
    for method in result['solutions']:
        method.pop('sourceRef', None)
    if isinstance(question, NormalizedQuestion):
        result['question']['prompt'] = question['Question']
        if 'choices' in result['question']:
            order = list(dict.fromkeys([*question['Choice Order'], *question['Choices']]))
            result['question']['choices'] = [{'id':key,'content':question['Choices'][key]} for key in order if key in question['Choices']]
        result['answer']['type'] = question['ResponseType']
        if 'accepted' in result['answer']:
            result['answer']['accepted'] = deepcopy(question['Accepted Responses'])
        result['solutions'] = [{'id':m['id'], 'title':m['label'],
            **{k:deepcopy(m[k]) for k in ('explanation','directNodeIds') if k in m}} for m in question['SolutionMethods']]
    return result


def mapping_for_v3(question, root=ROOT, baseline=None, *, known_node_ids=None):
    """Retain reviewed learning routes and distinguish each method's direct use."""
    from knowledge_graph import question_fingerprint, validate_mapping, GraphError
    question = normalize_question(question, root=root)
    if not is_v3(question):
        raise QuestionFormatError('mapping_for_v3 requires a v3 question.')
    raw = raw_question(question)
    has_baseline = bool(baseline)
    mapping = deepcopy(baseline or {})
    fingerprint = question_fingerprint(question, root)
    routes = deepcopy(mapping.get('routes', []))
    by_id = {route['id']:route for route in routes}
    previous_methods = {method_id:route['id'] for route in routes
                        for method_id in route.get('methodDirectNodeIds', {})}
    for route in routes:
        route['methodDirectNodeIds'] = {}
    for method in question['SolutionMethods']:
        legacy_id = method.get('legacyRouteId') if has_baseline else None
        route_id = legacy_id if legacy_id in by_id else None
        route_id = route_id or previous_methods.get(method['id']) or (method['id'] if method['id'] in by_id else None)
        direct = deepcopy(method.get('directNodeIds', []))
        if route_id is None:
            if not direct:
                continue
            route_id = method['id']
            route = {'id':route_id,'label':method['label'],'nodeIds':[], 'methodDirectNodeIds':{}}
            routes.append(route)
            by_id[route_id] = route
        route = by_id[route_id]
        route['methodDirectNodeIds'][method['id']] = direct
        route['nodeIds'] = list(dict.fromkeys([*route['nodeIds'], *direct]))
    for route in routes:
        if not route['methodDirectNodeIds']:
            route.pop('methodDirectNodeIds')
            route.pop('contextNodeIds', None)
            continue
        immediate = {node for ids in route['methodDirectNodeIds'].values() for node in ids}
        route['contextNodeIds'] = [node for node in route['nodeIds'] if node not in immediate]
    old_status = mapping.get('status')
    mapping.update(questionId=raw['id'], bank=raw['bank'], **fingerprint,
        assessedIds=deepcopy(raw['assessedNodeIds']), supportIds=deepcopy(mapping.get('supportIds', [])), routes=routes,
        reviewStatus=mapping.get('reviewStatus', 'user_asserted'),
        flags=deepcopy(mapping.get('flags', [])), answerCheck=deepcopy(mapping.get('answerCheck', {'status':'not_independently_reviewed'})),
        rationale='Format 3 projection preserves reviewed route identities and optional learning context. methodDirectNodeIds gives each compact method immediate concepts; contextNodeIds retains the rest of its route package separately. Shared support roles remain shared support.',
        reviews=deepcopy(mapping.get('reviews', [])))
    if old_status == 'non_diagnostic':
        if mapping['assessedIds'] or routes:
            raise GraphError(raw['id']+': definition-only history conflicts with assessed or method concepts; review the conversion.')
        mapping['status'] = 'non_diagnostic'
    else:
        mapping['status'] = 'unresolved' if old_status == 'unresolved' else ('mapped' if mapping['assessedIds'] or routes else 'unresolved')
    if mapping.get('headingContext'):
        if question.get('Topic', {}).get('label') != mapping['headingContext']:
            raise GraphError(raw['id']+': the required visible heading was lost in conversion.')
    mapping['reviews'].append({'stage':'question_format_v3_projection', 'decision':'projected_not_new_content_review',
        'sourceRef':raw['sourceRef'], 'priorMappingSHA256':hashlib.sha256(json.dumps(baseline,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest() if baseline else None,
        'meaning':'Format migration preserves earlier source review as history; it is not a fresh model or teacher review.'})
    known = known_node_ids if known_node_ids is not None else {n['id'] for n in json.loads((database_root(root)/'knowledge-graph/source/nodes.json').read_text(encoding='utf-8-sig'))}
    validate_mapping(mapping, known)
    return mapping
