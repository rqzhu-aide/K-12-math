"""The portable question-bank contract and paths shared by import and practice."""
import hashlib
from copy import deepcopy
import json
from pathlib import Path
from layout import database_root
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from question_answers import numeric_list, normalized

ROOT = Path(__file__).resolve().parents[2]
BANK_ID = re.compile(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*')
QUESTION_ID = re.compile(r'[A-Za-z0-9_]{1,120}')
AMC_QUESTION_ID = re.compile(r'\d{4}_(?:Fall_)?AMC_(?:8|10[AB]?|12[AB]?)_Q(?:0[1-9]|[1-4]\d|50)')
FIGURE = re.compile(r'\[Figure \d+\]\(([^)]+)\)')
FIGURE_PATH = re.compile(r'figures/[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:svg|png|jpg|jpeg|webp)')


class BankError(ValueError):
    """A bank cannot be used without an actionable correction."""


def _primary_reference_solution(question):
    """Share labeled source text, excluding a reviewed conflict with the task."""
    meta = question.get('Meta') or {}
    solution = question.get('Solution', '')
    if not isinstance(solution, str) or not solution.strip():
        solution = ''
    omitted = ''
    if (question.get('ID') == 'cnm_p167_q1'
            and question.get('Question') == 'Calculate: \\(1\\times3=?\\)'
            and solution == 'Multiply both the numerator and denominator of \\(\\frac{1}{2}\\) by 3. The new numerator is 3.'):
        solution = ''
        omitted = 'Reviewed mismatch: this question asks only for multiplication; fraction-equivalence details were omitted.'
    if not solution and meta.get('SolutionStatus') == 'Third-party worked solution not included in this distribution':
        omitted = meta['SolutionStatus']
    provenance = {'source': meta.get('SolutionSource') or 'Bank-provided solution; source not specified',
                  'reviewStatus': meta.get('SolutionStatus') or 'Review status not specified'}
    for source, target in (('SolutionSourceURL', 'sourceURL'), ('SourceRevision', 'sourceRevision')):
        if meta.get(source):
            provenance[target] = meta[source]
    availability = 'deliberately_omitted' if omitted else 'present' if solution else 'missing'
    return {'text': solution, 'availability': availability, 'provenance': provenance, 'omittedReason': omitted}


def optional_solution_methods(question, root=ROOT):
    """Validate a separately reviewed supplement without altering the primary source."""
    from question_format_v3 import is_v3
    if is_v3(question):
        # V3 already carries each method and its separate source reference.
        return None
    meta = question.get('Meta') or {}
    if 'OptionalSolutionReview' not in meta:
        return None
    try:
        from knowledge_graph import question_fingerprint
        qid = question.get('ID')
        pointer = meta['OptionalSolutionReview']
        expected_path = f'knowledge-graph/evidence/optional-solution-methods/{qid}.json'
        if (not isinstance(qid, str) or not QUESTION_ID.fullmatch(qid)
                or not isinstance(pointer, dict) or set(pointer) != {'path', 'sha256'}
                or pointer['path'] != expected_path or not _sha256_string(pointer['sha256'])):
            raise ValueError('the evidence pointer differs from the prescribed question path')
        base = _primary_reference_solution(question)
        if base['availability'] != 'present':
            raise ValueError('the primary worked solution is unavailable')
        base_root = database_root(root).resolve()
        path = (base_root / expected_path).resolve()
        if not path.is_relative_to(base_root / 'knowledge-graph/evidence/optional-solution-methods'):
            raise ValueError('the evidence leaves its prescribed folder')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != pointer['sha256']:
            raise ValueError('the evidence bytes differ from their hash')
        evidence = json.loads(data.decode('utf-8-sig'))
        if (evidence.get('schemaVersion') != 1 or evidence.get('kind') != 'reviewed_optional_solution_methods'
                or evidence.get('questionId') != qid
                or evidence.get('questionContentHash') != question_fingerprint(question, root)['contentHash']
                or evidence.get('primarySolutionSHA256') != hashlib.sha256(question['Solution'].encode('utf-8')).hexdigest()):
            raise ValueError('the supplement is not bound to this question and primary solution')
        methods = evidence.get('methods')
        if not isinstance(methods, list) or not 1 <= len(methods) <= 3:
            raise ValueError('the supplement needs one to three complete methods')
        catalog = json.loads((base_root / 'knowledge-graph/source/nodes.json').read_text(encoding='utf-8-sig'))
        known = {node['id'] for node in catalog}
        identifiers = set()
        figures = set(FIGURE.findall('\n'.join([question['Question'], *question['Choices'].values(), question['Solution']])))
        for method in methods:
            if (not isinstance(method, dict)
                    or set(method) != {'id', 'label', 'explanation', 'nodeIds', 'prerequisiteIds', 'levelReason'}
                    or any(not isinstance(method[k], str) or not method[k].strip()
                           for k in ('id', 'label', 'explanation', 'levelReason'))
                    or not re.sub(r'^Method\s+\d+:\s*', '', method['label']).strip()
                    or method['id'] in identifiers):
                raise ValueError('a method lacks its distinct identity, explanation, or scope')
            identifiers.add(method['id'])
            for key in ('nodeIds', 'prerequisiteIds'):
                ids = method[key]
                if (not isinstance(ids, list) or (key == 'nodeIds' and not ids)
                        or any(not isinstance(n, str) or n not in known for n in ids)
                        or len(ids) != len(set(ids))):
                    raise ValueError('a method names unsupported catalog concepts')
            if not set(FIGURE.findall(method['explanation'])) <= figures:
                raise ValueError('a method introduces an unsupplied figure')
        candidate = {key: evidence[key] for key in
                     ('questionId', 'questionContentHash', 'primarySolutionSHA256', 'methods')}
        candidate_hash = hashlib.sha256(json.dumps(candidate, ensure_ascii=False, sort_keys=True,
                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
        if evidence.get('candidateHash') != candidate_hash or evidence.get('reviewCandidateHash') != candidate_hash:
            raise ValueError('the accepted method candidate binding differs')
        review = evidence.get('review')
        checks = ('mathematicalCheck', 'levelCheck', 'methodDistinctness', 'annotationCheck')
        if (not isinstance(review, dict) or review.get('questionId') != qid
                or review.get('decision') != 'accept' or review.get('issues') != []
                or any(not isinstance(review.get(k), str) or not review[k].strip() for k in checks)):
            raise ValueError('the exact optional methods lack an accepted independent review')
        for role in ('author', 'reviewer'):
            identity = evidence.get(role)
            if not isinstance(identity, dict) or any(not isinstance(identity.get(k), str) or not identity[k].strip()
                                                    for k in ('model', 'effort')):
                raise ValueError('the author or independent reviewer identity is missing')
        origin = evidence.get('origin')
        if (not isinstance(origin, dict) or origin.get('separateFreshReview') is not True
                or any(not _sha256_string(origin.get(k)) for k in
                       ('reviewerInputHash', 'reviewerResponseHash'))):
            raise ValueError('the independent reviewer evidence bindings are missing')
        if 'authorArtifact' in origin:
            artifact = origin['authorArtifact']
            if ('authorResponseHash' in origin or not isinstance(artifact, dict)
                    or artifact.get('kind') != 'native_subagent_authored_candidate'
                    or artifact.get('fileName') != qid + '.json'
                    or artifact.get('candidateHash') != candidate_hash
                    or not _sha256_string(artifact.get('sha256'))):
                raise ValueError('the authored file is not bound to this candidate')
        elif not _sha256_string(origin.get('authorResponseHash')):
            raise ValueError('the author evidence binding is missing')
        provenance = {'source': 'Math Practice optional solution methods',
                      'reviewStatus': 'AI-authored and independently AI-reviewed; not teacher reviewed',
                      'sourceURL': 'https://github.com/rqzhu-aide/math-practice',
                      'evidence': dict(pointer)}
        attribution = evidence.get('attribution', {})
        if 'officialSolution' in attribution:
            booklet = attribution['officialSolution']
            if not isinstance(booklet, dict) or not booklet.get('attribution') or booklet != meta.get('OfficialSolution'):
                raise ValueError('the credited official booklet differs from the question source')
            provenance['source'] = 'Math Practice explanations adapted from the official ' + str(booklet['label']) + ' booklet by ' + booklet['attribution']
            provenance['sourceURL'] = booklet['sourceURL']
        return {'methods': [{'id': m['id'], 'label': re.sub(r'^Method\s+\d+:\s*', '', m['label']).strip(),
                              'explanation': m['explanation']} for m in methods],
                'provenance': provenance}
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise BankError('Optional solution methods are unavailable: ' + str(exc)) from None


def _sha256_string(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def browser_optional_solution(question, root=ROOT):
    """Add only validated static content; unaugmented browser records stay identical."""
    optional = optional_solution_methods(question, root)
    return ({'optionalSolutionMethods': optional['methods'],
             'optionalSolutionProvenance': optional['provenance']} if optional else {})


def reference_solution(question, root=ROOT):
    """Compose the same labelled optional methods for the single tutor reference."""
    from question_format_v3 import is_v3, normalize_question
    if is_v3(question):
        question = normalize_question(question, root=root)
        methods = [m for m in question['SolutionMethods'] if m.get('explanation')
                   and _primary_reference_solution({**question, 'Solution':m['explanation']})['availability'] == 'present']
        text = '\n\n'.join(f'Method {i}: {m["label"]}\n\n{m["explanation"]}'
                            for i, m in enumerate(methods, 1))
        base = _primary_reference_solution(question)
        return {'text':text, 'availability':'present' if methods else base['availability'], 'omittedReason':'' if methods else base['omittedReason'],
                'provenance':{'source':'Individually credited question-format 3 methods',
                    'reviewStatus':'See each method source; format migration is not a new content review.',
                    'methods':[{'id':m['id'], **m['provenance']} for m in methods]}}
    result = _primary_reference_solution(question)
    if 'OptionalSolutionReview' not in (question.get('Meta') or {}):
        return result
    try:
        optional = optional_solution_methods(question, root)
    except BankError:
        result['provenance']['optionalMethods'] = {'status': 'omitted',
            'reason': 'The optional-method evidence is unavailable or no longer matches the displayed task and primary solution.'}
        return result
    result['text'] += ''.join(f'\n\nOptional method {i}: {m["label"]}\n\n{m["explanation"]}'
                              for i, m in enumerate(optional['methods'], 1))
    result['provenance']['optionalMethods'] = optional['provenance']
    return result


def valid_bank_id(value):
    return isinstance(value, str) and len(value) <= 48 and bool(BANK_ID.fullmatch(value))


def read_json(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise BankError(f'{path.name}: cannot read valid JSON ({exc}).') from None
    if not isinstance(value, dict):
        raise BankError(f'{path.name}: expected a JSON object.')
    return value


def load_question(path, root=ROOT):
    """Normalize at the file boundary; retain legacy v2 objects unchanged."""
    from question_format_v3 import normalize_question, QuestionFormatError
    path = Path(path)
    try:
        return normalize_question(read_json(path), root=root, bank_root=path.parent.parent)
    except QuestionFormatError as exc:
        raise BankError(f'{path.name}: {exc}') from None


def required_text(value, key, context):
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise BankError(f'{context}: {key} must be a nonempty string.')
    return item


def source_url(value, context):
    if not isinstance(value, str) or not value or re.search(r'\s', value):
        raise BankError(f'{context}: source URL must be a nonempty http(s) URL without whitespace.')
    if value:
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password
        except ValueError:
            valid = False
        if not valid:
            raise BankError(f'{context}: use an http(s) source URL without credentials.')


def validate_manifest(manifest):
    if not valid_bank_id(manifest.get('id')):
        raise BankError('bank.json: id must use lowercase letters, digits and single internal underscores (max 48 characters).')
    for key in ('label', 'attribution', 'license'):
        required_text(manifest, key, 'bank.json')
    if 'sourceURL' in manifest:
        source_url(manifest['sourceURL'], 'bank.json')


def validate_question(question, manifest, filename):
    context = filename
    question_id = required_text(question, 'ID', context)
    if (not QUESTION_ID.fullmatch(question_id) or not question_id.startswith(manifest['id'] + '__')
            or len(question_id) <= len(manifest['id']) + 2 or filename != question_id + '.json'):
        raise BankError(f'{context}: ID must start with {manifest["id"]}__, use letters/digits/underscores, and match the filename (max 120 characters).')
    if question.get('Bank') != manifest['id'] or question.get('SchemaVersion') != '2.0':
        raise BankError(f'{context}: Bank must match bank.json and SchemaVersion must be "2.0".')
    for key in ('Language', 'Level', 'CurriculumUnit', 'Batch', 'Question', 'Correct Answer', 'Solution'):
        required_text(question, key, context)
    for key, minimum in (('Grade', 0), ('Number', 1)):
        if type(question.get(key)) is not int or question[key] < minimum:
            raise BankError(f'{context}: {key} must be an integer of at least {minimum}.')
    topic = question.get('Topic')
    if not isinstance(topic, dict):
        raise BankError(f'{context}: Topic must contain id and label.')
    for key in ('id', 'label'):
        required_text(topic, key, context + ' Topic')
    if topic['id'] != question['Batch']:
        raise BankError(f'{context}: Batch must equal Topic.id.')
    kind = question.get('ResponseType')
    if kind not in ('choice', 'numeric', 'short', 'self'):
        raise BankError(f'{context}: ResponseType must be choice, numeric, short or self.')
    choices = question.get('Choices')
    if not isinstance(choices, dict):
        raise BankError(f'{context}: Choices must be an object.')
    if kind == 'choice':
        if (not 2 <= len(choices) <= 5 or any(key not in 'ABCDE' or len(key) != 1 for key in choices)
                or any(not isinstance(v, str) or not v.strip() for v in choices.values())
                or question['Correct Answer'] not in choices):
            raise BankError(f'{context}: choice questions need 2-5 nonempty A-E choices and a Correct Answer naming a supplied choice.')
    elif choices:
        raise BankError(f'{context}: use empty Choices for {kind} questions.')
    if kind == 'numeric':
        try:
            numeric_list(question['Correct Answer'])
        except (ValueError, ZeroDivisionError):
            raise BankError(f'{context}: numeric answers must be numbers, fractions, or comma-separated lists, without units or LaTeX.') from None
    for key, pattern in (('domain', r'domain:[a-z0-9-]+'), ('skill', r'skill:[a-zA-Z0-9:_-]+'),
                         ('Accepted Answers', None), ('Rejected Answers', None)):
        values = question.get(key, [] if key.endswith('Answers') else None)
        if (not isinstance(values, list) or (pattern and not values) or any(not isinstance(v, str) or not v.strip() or (pattern and not re.fullmatch(pattern, v)) for v in values)
                or len(values) != len(set(values))):
            raise BankError(f'{context}: {key} must be a list of unique valid strings.')
    if kind != 'short' and question.get('Accepted Answers'):
        raise BankError(f'{context}: Accepted Answers is supported only for short answers.')
    accepted = {normalized(x) for x in [question['Correct Answer'], *question.get('Accepted Answers', [])]}
    if accepted.intersection(normalized(x) for x in question.get('Rejected Answers', [])):
        raise BankError(f'{context}: an answer cannot be both accepted and rejected.')
    for key, options in (('Question Type', ('text', 'mixed', 'figure')), ('Choices Type', ('text', 'figure')),
                         ('GradingStatus', ('gradable', 'disputed')), ('Answer Form', ('decimal', 'standard-monomial', 'ordered-list'))):
        if key in question and question[key] not in options:
            raise BankError(f'{context}: unsupported {key}.')
    if 'Unordered Answers' in question and type(question['Unordered Answers']) is not bool:
        raise BankError(f'{context}: Unordered Answers must be true or false.')
    if question.get('GradingStatus') == 'disputed':
        required_text(question, 'GradingNote', context)
    if 'Year' in question and question['Year'] is not None and type(question['Year']) is not int:
        raise BankError(f'{context}: Year must be an integer or null.')
    for key in ('Area', 'Difficulty', 'GradingNote'):
        if key in question and not isinstance(question[key], str):
            raise BankError(f'{context}: {key} must be a string.')
    meta = question.get('Meta')
    if not isinstance(meta, dict):
        raise BankError(f'{context}: Meta must contain attribution, license and solution source.')
    for key in ('Attribution', 'License', 'SolutionSource'):
        required_text(meta, key, context + ' Meta')
    if 'SourceURL' in meta:
        source_url(meta['SourceURL'], context)
    sources = meta.get('FigureSources', {})
    if not isinstance(sources, dict) or any(not isinstance(v, dict) or ('alt' in v and not isinstance(v['alt'], str)) for v in sources.values()):
        raise BankError(f'{context}: Meta.FigureSources must map figure paths to objects with optional alt text.')
    translation = meta.get('Translation', {})
    if not isinstance(translation, dict) or ('status' in translation and not isinstance(translation['status'], str)):
        raise BankError(f'{context}: Meta.Translation must be an object with optional string status.')


def figure_path(bank_root, relative):
    if not isinstance(relative, str) or not FIGURE_PATH.fullmatch(relative):
        raise BankError('Figures must use a flat figures/filename.svg, .png, .jpg, .jpeg or .webp path.')
    base = bank_root.resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base / 'figures') or not path.is_file():
        raise BankError(f'{relative}: figure is missing or outside the bank figures folder.')
    return path


def validate_figure(path):
    data = path.read_bytes()
    if path.suffix == '.svg':
        try:
            if re.search(br'<!\s*(?:DOCTYPE|ENTITY)|<\?xml-stylesheet', data, re.I):
                raise ValueError()
            tree = ET.fromstring(data)
            if tree.tag.split('}')[-1] != 'svg':
                raise ValueError()
            forbidden = {'script', 'foreignobject', 'iframe', 'object', 'embed', 'audio', 'video',
                         'animate', 'animatetransform', 'animatemotion', 'set', 'discard'}
            for element in tree.iter():
                if element.tag.split('}')[-1].lower() in forbidden:
                    raise ValueError()
                for key, value in element.attrib.items():
                    name = key.split('}')[-1].lower()
                    if name.startswith('on') or name == 'base' or (name in ('href', 'src') and not value.startswith('#')):
                        raise ValueError()
                    if name == 'style' and '\\' in value:
                        raise ValueError()
                if element.tag.split('}')[-1].lower() == 'style' and '\\' in (element.text or ''):
                    raise ValueError()
            # Local paint-server references are fine; external CSS resources are not.
            text = data.decode('utf-8')
            if '@import' in text.lower() or any(not value.strip().strip('\'"').startswith('#') for value in re.findall(r'url\s*\(([^)]*)\)', text, re.I)):
                raise ValueError()
        except (ValueError, ET.ParseError, UnicodeError):
            raise BankError(f'{path.name}: use a static, self-contained SVG without scripts, events, animation or external resources.') from None
    else:
        signatures = {'.png': data.startswith(b'\x89PNG\r\n\x1a\n'),
                      '.jpg': data.startswith(b'\xff\xd8\xff'), '.jpeg': data.startswith(b'\xff\xd8\xff'),
                      '.webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP'}
        if not signatures.get(path.suffix):
            raise BankError(f'{path.name}: image contents do not match the file extension.')
    return data


def read_bank(source, graph_root=ROOT):
    source = Path(source).resolve()
    manifest = read_json(source / 'bank.json')
    validate_manifest(manifest)
    records, figures, units, topics, numbers = [], {}, {}, {}, set()
    for path in sorted((source / 'questions').glob('*.json')):
        if not path.resolve().is_relative_to(source / 'questions'):
            raise BankError(f'{path.name}: question file must stay inside the bank.')
        question = load_question(path, root=graph_root)
        from question_format_v3 import is_v3
        if is_v3(question):
            if (question['Bank'] != manifest['id'] or not question['ID'].startswith(manifest['id']+'__')
                    or path.name != question['ID']+'.json'):
                raise BankError(f'{path.name}: custom question ID, bank and filename must agree.')
        else:
            validate_question(question, manifest, path.name)
        group = (question.get('Level'), question.get('Grade'))
        topic = (*group, question.get('Batch'))
        number = (*topic, question.get('Number', question['ID']))
        unit, label = question.get('CurriculumUnit'), question.get('Topic', {}).get('label')
        if (units.setdefault(group, unit) != unit
                or topics.setdefault(topic, label) != label or number in numbers):
            raise BankError(f'{path.name}: keep unit/topic labels consistent and problem numbers unique within each level, grade and topic.')
        numbers.add(number)
        method_texts = [m['explanation'] for m in question.get('SolutionMethods', []) if m.get('explanation')]
        for text in [question['Question'], question['Solution'], *question['Choices'].values(), *method_texts]:
            for relative in FIGURE.findall(text):
                if relative not in figures:
                    figures[relative] = validate_figure(figure_path(source, relative))
        if 'KnowledgeGraph' in question:
            from knowledge_graph import GraphError
            from question_graph import validate_imported_references
            try:
                validate_imported_references(question, root=graph_root, bank_root=source)
            except GraphError as exc:
                raise BankError(f'{path.name}: {exc}') from None
        records.append(question)
    if not records:
        raise BankError('questions/: add at least one JSON question file.')
    if any(is_v3(question) for question in records):
        from question_format_v3 import portable_source_files, QuestionFormatError
        try:
            portable_source_files(source)
        except QuestionFormatError as exc:
            raise BankError(str(exc)) from None
    return manifest, records, figures


def browser_bank(manifest, records, root=ROOT):
    fields = {'id': 'ID', 'bank': 'Bank', 'year': 'Year', 'level': 'Level', 'grade': 'Grade',
              'unit': 'CurriculumUnit', 'batch': 'Batch', 'number': 'Number', 'area': 'Area', 'topic': 'Topic',
              'domain': 'domain', 'skill': 'skill', 'responseType': 'ResponseType', 'question': 'Question',
              'questionType': 'Question Type', 'choices': 'Choices', 'choicesType': 'Choices Type',
              'answer': 'Correct Answer', 'acceptedAnswers': 'Accepted Answers', 'unorderedAnswers': 'Unordered Answers',
              'gradingStatus': 'GradingStatus', 'gradingNote': 'GradingNote', 'answerForm': 'Answer Form',
              'rejectedAnswers': 'Rejected Answers', 'solution': 'Solution',
              'knowledgeGraph': 'KnowledgeGraph'}
    questions = []
    for record in records:
        from question_format_v3 import is_v3
        if is_v3(record):
            questions.append(browser_question(record, root=root, manifest=manifest))
            continue
        item = {display: record[key] for display, key in fields.items() if key in record}
        meta = record['Meta']
        item.update(solutionSource=meta['SolutionSource'], sourceURL=meta.get('SourceURL', manifest.get('sourceURL', '')),
                    figureSources=meta.get('FigureSources', {}), translationStatus=meta.get('Translation', {}).get('status', ''))
        item.update(browser_optional_solution(record, root))
        questions.append(item)
    return {key: manifest[key] for key in ('id', 'label', 'attribution', 'license', 'sourceURL') if key in manifest} | {
        'figuresBase': f'../custom-banks/{manifest["id"]}/figures/', 'questions': questions}


def browser_question(record, *, root=ROOT, manifest=None):
    """A common per-question v3 browser projection for built-in and custom banks."""
    from question_format_v3 import normalize_question, is_v3
    record = normalize_question(record, root=root)
    if not is_v3(record):
        if record.get('Bank') == 'amc':
            from export_amc_bank import browser_question as amc_question
            return amc_question(record, root=root)
        if manifest is None:
            meta = record.get('Meta', {})
            manifest = {'id':record['Bank'], 'label':record['Bank'], 'attribution':meta.get('Attribution',''),
                        'license':meta.get('License','')}
        return browser_bank(manifest, [record], root=root)['questions'][0]
    fields = {'id':'ID','bank':'Bank','year':'Year','level':'Level','grade':'Grade','unit':'CurriculumUnit',
        'batch':'Batch','number':'Number','area':'Area','topic':'Topic','domain':'domain','skill':'skill',
        'responseType':'ResponseType','question':'Question','questionType':'Question Type','choices':'Choices',
        'choiceOrder':'Choice Order','choicesType':'Choices Type','answer':'Correct Answer',
        'acceptedResponses':'Accepted Responses','answerRubric':'Answer Rubric','rejectedAnswers':'Rejected Answers',
        'unorderedAnswers':'Unordered Answers','gradingStatus':'GradingStatus','gradingNote':'GradingNote',
        'answerForm':'Answer Form','solution':'Solution','solutionMethods':'SolutionMethods','sourceInfo':'SourceInfo',
        'knowledgeGraph':'KnowledgeGraph'}
    item = {display:deepcopy(record[key]) for display,key in fields.items() if key in record}
    meta = record['Meta']
    item.update(schemaVersion='3.0', sourceRef=record['SourceRef'],
        figureSources=deepcopy(meta.get('FigureSources', {})), sourceURL=meta.get('SourceURL',''),
        solutionSource=meta.get('SolutionSource',''), solutionSourceURL=meta.get('SolutionSourceURL',''),
        editorialNote=meta.get('EditorialNote', '') or record.get('Source Content Note', ''),
        translationStatus=meta.get('Translation', {}).get('status', ''))
    if meta.get('OfficialSolution'):
        item['officialSolution'] = deepcopy(meta['OfficialSolution'])
    solution = reference_solution(record, root=root)
    item.update(solutionAvailability=solution['availability'], solutionOmittedReason=solution['omittedReason'],
                solutionStatus=meta.get('SolutionStatus',''))
    return item


def custom_root(root=ROOT):
    base = root.resolve()
    target = (base / 'custom-banks').resolve()
    if not target.is_relative_to(base) or target == base:
        raise BankError('custom-banks must be a folder inside this checkout.')
    return target


def custom_question_path(question_id, root=ROOT):
    if not isinstance(question_id, str) or not QUESTION_ID.fullmatch(question_id) or '__' not in question_id:
        return None
    bank_id, suffix = question_id.split('__', 1)
    if not valid_bank_id(bank_id) or not suffix:
        return None
    base = custom_root(root)
    bank = (base / bank_id).resolve()
    if not bank.is_relative_to(base) or not (bank / 'bank.json').is_file():
        return None
    path = (bank / 'questions' / (question_id + '.json')).resolve()
    return path if path.is_relative_to(bank / 'questions') else None


def bank_root_for_question(question, root=ROOT):
    if question.get('Bank') == 'cn-math':
        return database_root(root) / 'cn-math-bank'
    if (question.get('Bank') == 'amc' and isinstance(question.get('ID'), str)
            and AMC_QUESTION_ID.fullmatch(question['ID'])):
        return database_root(root) / 'amc-bank'
    path = custom_question_path(question.get('ID'), root)
    if path is None or question.get('Bank') != question['ID'].split('__', 1)[0]:
        raise BankError('This question does not belong to an installed bank.')
    return path.parent.parent


def custom_asset_path(relative, root=ROOT):
    """Only the browser bundle and referenced installed images are public assets."""
    base = custom_root(root)
    if relative == 'custom-banks/banks.js':
        path = (base / 'banks.js').resolve()
        return path if path.is_relative_to(base) else None
    parts = relative.split('/')
    if len(parts) != 4 or parts[0] != 'custom-banks' or not valid_bank_id(parts[1]):
        return None
    bank = (base / parts[1]).resolve()
    if not bank.is_relative_to(base) or not (bank / 'bank.json').is_file():
        return None
    try:
        return figure_path(bank, '/'.join(parts[2:]))
    except BankError:
        return None
