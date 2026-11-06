"""The portable question-bank contract and paths shared by import and practice."""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from question_answers import numeric_list, normalized

ROOT = Path(__file__).resolve().parents[1]
BANK_ID = re.compile(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*')
QUESTION_ID = re.compile(r'[A-Za-z0-9_]{1,120}')
AMC_QUESTION_ID = re.compile(r'\d{4}_(?:Fall_)?AMC_(?:8|10[AB]?|12[AB]?)_Q(?:0[1-9]|[1-4]\d|50)')
FIGURE = re.compile(r'\[Figure \d+\]\(([^)]+)\)')
FIGURE_PATH = re.compile(r'figures/[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:svg|png|jpg|jpeg|webp)')


class BankError(ValueError):
    """A bank cannot be used without an actionable correction."""


def reference_solution(question):
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
        question = read_json(path)
        validate_question(question, manifest, path.name)
        group = (question['Level'], question['Grade'])
        topic = (*group, question['Batch'])
        number = (*topic, question['Number'])
        if (units.setdefault(group, question['CurriculumUnit']) != question['CurriculumUnit']
                or topics.setdefault(topic, question['Topic']['label']) != question['Topic']['label'] or number in numbers):
            raise BankError(f'{path.name}: keep unit/topic labels consistent and problem numbers unique within each level, grade and topic.')
        numbers.add(number)
        for text in [question['Question'], question['Solution'], *question['Choices'].values()]:
            for relative in FIGURE.findall(text):
                if relative not in figures:
                    figures[relative] = validate_figure(figure_path(source, relative))
        if 'KnowledgeGraph' in question:
            from knowledge_graph import GraphError
            from knowledge_graph_questions import validate_imported_references
            try:
                validate_imported_references(question, root=graph_root, bank_root=source)
            except GraphError as exc:
                raise BankError(f'{path.name}: {exc}') from None
        records.append(question)
    if not records:
        raise BankError('questions/: add at least one JSON question file.')
    return manifest, records, figures


def browser_bank(manifest, records):
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
        item = {display: record[key] for display, key in fields.items() if key in record}
        meta = record['Meta']
        item.update(solutionSource=meta['SolutionSource'], sourceURL=meta.get('SourceURL', manifest.get('sourceURL', '')),
                    figureSources=meta.get('FigureSources', {}), translationStatus=meta.get('Translation', {}).get('status', ''))
        questions.append(item)
    return {key: manifest[key] for key in ('id', 'label', 'attribution', 'license', 'sourceURL') if key in manifest} | {
        'figuresBase': f'../custom-banks/{manifest["id"]}/figures/', 'questions': questions}


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
        return root / 'cn-math-bank'
    if (question.get('Bank') == 'amc' and isinstance(question.get('ID'), str)
            and AMC_QUESTION_ID.fullmatch(question['ID'])):
        return root / 'amc-bank'
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
