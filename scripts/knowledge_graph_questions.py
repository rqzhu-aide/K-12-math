"""Bind reviewed graph records to installed questions and refresh browser metadata.

Only KnowledgeGraph / knowledgeGraph changes. Question text, mathematics,
answers, source metadata, and the other browser fields are preserved.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import tempfile

from knowledge_graph import (GraphError, graph_version as database_graph_version, load_source,
                             mapping_record, node_ids, question_fingerprint, validate_mapping,
                             validate_heading_context)
from question_answers import confirmed_grading_notice
from question_banks import ROOT, bank_root_for_question, read_json, valid_bank_id


GRAPH_FIELDS = ('contentHash', 'status', 'reviewStatus', 'assessedIds', 'supportIds', 'routes', 'flags')
GRADING_FIELDS = ('gradingStatus', 'gradingNote')
BROWSER_BINDING_FIELDS = {
    'question': 'Question', 'choices': 'Choices', 'answer': 'Correct Answer',
    'responseType': 'ResponseType', 'level': 'Level', 'grade': 'Grade',
    'unit': 'CurriculumUnit', 'year': 'Year', 'batch': 'Batch', 'number': 'Number',
    'questionType': 'Question Type', 'choicesType': 'Choices Type',
    'acceptedAnswers': 'Accepted Answers', 'rejectedAnswers': 'Rejected Answers',
    'unorderedAnswers': 'Unordered Answers', 'gradingStatus': 'GradingStatus',
    'gradingNote': 'GradingNote', 'answerForm': 'Answer Form',
}


def graph_version(metadata):
    return str(metadata.get('version') or metadata.get('graphVersion') or metadata.get('schemaVersion') or '1')


def graph_payload(mapping, version):
    """The portable question stub; evidence and topology remain central."""
    payload = {'version': str(version), **{key: deepcopy(mapping.get(key, [] if key in
               ('assessedIds', 'supportIds', 'routes', 'flags') else None)) for key in GRAPH_FIELDS}}
    payload.update(confirmed_grading_notice(mapping.get('answerCheck')) or {})
    if 'headingContext' in mapping:
        payload['headingContext'] = mapping['headingContext']
    if 'contextualIds' in mapping:
        payload['contextualIds'] = deepcopy(mapping['contextualIds'])
    return payload


def validate_imported_references(question, root=ROOT, *, bank_root=None):
    """Check explicit custom references without turning a supplied claim into a review.

    An exact copy of a central mapping keeps its recorded review provenance.
    Other valid references must say user_asserted; ordinary banks need no graph.
    """
    if 'KnowledgeGraph' not in question:
        return
    stub = question['KnowledgeGraph']
    required = {'version', *GRAPH_FIELDS}
    if not isinstance(stub, dict) or not required.issubset(stub):
        raise GraphError('KnowledgeGraph must contain version, contentHash, status, reviewStatus, '
                         'assessedIds, supportIds, routes and flags.')
    try:
        ids = node_ids(root=root)
        version = database_graph_version(root=root)
        central = mapping_record(question['ID'], root=root)
    except GraphError as exc:
        raise GraphError('Explicit KnowledgeGraph references need the installed central graph database. '
                         f'Build it first, or omit KnowledgeGraph for ordinary practice. ({exc})') from None
    if stub['version'] != version:
        raise GraphError('KnowledgeGraph.version differs from the installed graph; refresh the references.')
    fingerprint = question_fingerprint(question, root=root, bank_root=bank_root)
    if stub['contentHash'] != fingerprint['contentHash']:
        raise GraphError('KnowledgeGraph content binding is stale; remap the displayed question and figures.')
    validate_heading_context(stub, question)
    if (central is not None and central.get('bank') == question.get('Bank')
            and central.get('contentHash') == fingerprint['contentHash']
            and central.get('figureHashes') == fingerprint['figureHashes']
            and central.get('headingContext') == stub.get('headingContext')
            and central.get('contextualIds', []) == stub.get('contextualIds', [])
            and all(stub[key] == graph_payload(central, version)[key] for key in required)):
        validate_mapping(central, ids)
        # These are controlled projections of central adjudication, not claims
        # accepted from an imported stub. Refresh older exact central exports.
        notice = confirmed_grading_notice(central.get('answerCheck')) or {}
        for field in GRADING_FIELDS:
            if field in notice:
                stub[field] = notice[field]
            else:
                stub.pop(field, None)
        return
    if any(field in stub for field in GRADING_FIELDS):
        raise GraphError('Imported graph grading notices must come from an exact central mapping. '
                         'Omit gradingStatus and gradingNote from user_asserted graph references.')
    if stub['reviewStatus'] != 'user_asserted':
        raise GraphError('Imported graph references do not match a central reviewed mapping. '
                         'Use reviewStatus "user_asserted", or refresh them from the central mapping.')
    mapping = {key: deepcopy(stub[key]) for key in GRAPH_FIELDS}
    if 'headingContext' in stub:
        mapping['headingContext'] = stub['headingContext']
    if 'contextualIds' in stub:
        mapping['contextualIds'] = deepcopy(stub['contextualIds'])
    mapping.update(questionId=question['ID'], bank=question['Bank'],
                   figureHashes=fingerprint['figureHashes'],
                   rationale='User-provided references; no central review is asserted.',
                   answerCheck={'status': 'not_independently_reviewed'}, reviews=[])
    validate_mapping(mapping, ids)


def _without_graph(value, field):
    return {key: item for key, item in value.items() if key != field}


def installed_questions(root=ROOT):
    """Read the installed banks once, retaining exact bytes for preservation checks."""
    root = Path(root).resolve()
    banks = [(root / 'cn-math-bank', 'cn-math'), (root / 'amc-bank', 'amc')]
    custom = root / 'custom-banks'
    if custom.exists():
        banks.extend((path, path.name) for path in sorted(custom.iterdir())
                     if path.is_dir() and valid_bank_id(path.name) and (path / 'bank.json').is_file())
    records, seen = [], set()
    for bank, bank_id in banks:
        if not bank.exists():
            continue
        for path in sorted((bank / 'questions').glob('*.json')):
            if not path.resolve().is_relative_to(bank.resolve() / 'questions'):
                raise GraphError(f'{path.name}: question file leaves its installed bank.')
            before = path.read_bytes()
            try:
                question = json.loads(before.decode('utf-8-sig'))
            except (ValueError, UnicodeError) as exc:
                raise GraphError(f'{path.name}: cannot read question JSON ({exc}).') from None
            if (not isinstance(question, dict) or question.get('Bank') != bank_id
                    or path.name != str(question.get('ID')) + '.json'):
                raise GraphError(f'{path.name}: question ID, bank and filename must agree.')
            if question['ID'] in seen:
                raise GraphError(f'{question["ID"]}: repeated installed question ID.')
            seen.add(question['ID'])
            if bank_root_for_question(question, root).resolve() != bank.resolve():
                raise GraphError(f'{path.name}: question resolves to another bank.')
            records.append({'path': path, 'before': before, 'question': question})
    return records


def _source_index(root, source_dir):
    source = load_source(root=root, source_dir=source_dir)
    nodes = {node['id'] for node in source['nodes']}
    mappings = {}
    for mapping in source['mappings']:
        validate_mapping(mapping, nodes)
        question_id = mapping['questionId']
        if question_id in mappings:
            raise GraphError(f'{question_id}: repeated source mapping.')
        mappings[question_id] = mapping
    return graph_version(source['metadata']), mappings


def _bound_payload(question, mapping, version, root):
    question_id = question['ID']
    if mapping.get('bank') != question.get('Bank'):
        raise GraphError(f'{question_id}: mapping bank does not match the installed question.')
    fingerprint = question_fingerprint(question, root=root)
    if mapping.get('contentHash') != fingerprint['contentHash']:
        raise GraphError(f'{question_id}: mapping is stale; displayed content or figures changed.')
    if 'figureHashes' in mapping and mapping['figureHashes'] != fingerprint['figureHashes']:
        raise GraphError(f'{question_id}: mapping figure hashes do not match.')
    validate_heading_context(mapping, question)
    return graph_payload(mapping, version)


def _read_bundle(path, variable):
    before = path.read_bytes()
    text = before.decode('utf-8-sig')
    match = re.search(r'\bwindow\.' + re.escape(variable) + r'\s*=\s*', text)
    if not match:
        raise GraphError(f'{path.name}: expected window.{variable} JSON assignment.')
    try:
        payload, end = json.JSONDecoder().raw_decode(text[match.end():])
    except ValueError as exc:
        raise GraphError(f'{path.name}: invalid browser-bank JSON ({exc}).') from None
    end += match.end()
    if text[end:].strip() != ';':
        raise GraphError(f'{path.name}: unexpected content after browser-bank JSON.')
    return before, text[:match.end()], payload, text[end:]


def _refresh_items(items, questions, context):
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise GraphError(f'{context}: questions must be an array.')
    if len(items) != len(questions) or {item.get('id') for item in items} != set(questions):
        raise GraphError(f'{context}: browser and installed question IDs differ; rebuild the bank first.')
    changed = False
    for item in items:
        question = questions[item['id']]
        for browser_key, source_key in BROWSER_BINDING_FIELDS.items():
            if browser_key in item and source_key in question and item[browser_key] != question[source_key]:
                raise GraphError(f'{item["id"]}: browser {browser_key} differs from the installed question; rebuild the bank first.')
        before = deepcopy(item)
        if 'KnowledgeGraph' in question:
            if 'headingContext' in question['KnowledgeGraph']:
                validate_heading_context(question['KnowledgeGraph'], {'ID': item['id'], 'Topic': item.get('topic')})
            item['knowledgeGraph'] = deepcopy(question['KnowledgeGraph'])
        else:
            item.pop('knowledgeGraph', None)
        if _without_graph(item, 'knowledgeGraph') != _without_graph(before, 'knowledgeGraph'):
            raise GraphError(f'{item["id"]}: browser refresh changed a non-graph field.')
        changed |= item != before
    return changed


def _bundle_changes(root, records):
    root = Path(root)
    by_bank = {}
    for record in records:
        question = record['question']
        by_bank.setdefault(question['Bank'], {})[question['ID']] = question
    changes = []
    for bank_id, folder, variable in (('cn-math', 'cn-math-bank', 'CN_MATH_BANK'),
                                      ('amc', 'amc-bank', 'AMC_BANK')):
        if bank_id not in by_bank:
            continue
        path = root / folder / 'bank.js'
        if not path.is_file():
            raise GraphError(f'{folder}/bank.js is missing; rebuild the browser bank first.')
        before, prefix, payload, suffix = _read_bundle(path, variable)
        if not isinstance(payload, dict):
            raise GraphError(f'{folder}/bank.js: expected a bank object.')
        if _refresh_items(payload.get('questions'), by_bank[bank_id], folder):
            after = (prefix + json.dumps(payload, ensure_ascii=False, indent=0) + suffix).encode('utf-8')
            changes.append((path, before, after))
    custom = {key: value for key, value in by_bank.items() if key not in ('cn-math', 'amc')}
    if custom:
        path = root / 'custom-banks/banks.js'
        before, prefix, payload, suffix = _read_bundle(path, 'CUSTOM_MATH_BANKS')
        if (not isinstance(payload, list) or len(payload) != len(custom)
                or {bank.get('id') for bank in payload} != set(custom)):
            raise GraphError('custom-banks/banks.js: installed bank IDs differ; import the banks again first.')
        changed = False
        for bank in payload:
            changed |= _refresh_items(bank.get('questions'), custom[bank['id']], bank['id'])
        if changed:
            after = (prefix + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + suffix).encode('utf-8')
            changes.append((path, before, after))
    return changes


def _atomic_bytes(path, data):
    descriptor, name = tempfile.mkstemp(prefix='.graph-', suffix='.tmp', dir=path.parent)
    pending = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
        os.replace(pending, path)
    finally:
        if pending.exists():
            pending.unlink()


def _commit_changes(changes, verify=None):
    """Preflight all files, then restore our writes if verification fails."""
    for path, before, _ in changes:
        if path.read_bytes() != before:
            raise GraphError(f'{path.name}: changed during preflight; rerun before applying graph metadata.')
    written = []
    try:
        for path, before, after in changes:
            if path.read_bytes() != before:
                raise GraphError(f'{path.name}: changed while applying graph metadata.')
            _atomic_bytes(path, after)
            written.append((path, before, after))
            if path.read_bytes() != after:
                raise GraphError(f'{path.name}: written graph metadata did not verify.')
        if verify:
            verify()
    except Exception:
        for path, before, after in reversed(written):
            if path.read_bytes() == after:
                _atomic_bytes(path, before)
        raise


def apply_mappings(root=ROOT, source_dir=None, *, dry_run=True, refresh_browsers=True, require_complete=False):
    root = Path(root).resolve()
    version, mappings = _source_index(root, source_dir)
    records = installed_questions(root)
    changes, missing, expected = [], [], {}
    statuses = {'mapped': 0, 'non_diagnostic': 0, 'unresolved': 0}
    for record in records:
        question = record['question']
        mapping = mappings.get(question['ID'])
        if mapping is None:
            missing.append(question['ID'])
            continue
        payload = _bound_payload(question, mapping, version, root)
        after = {**question, 'KnowledgeGraph': payload}
        if _without_graph(after, 'KnowledgeGraph') != _without_graph(question, 'KnowledgeGraph'):
            raise GraphError(f'{question["ID"]}: applying metadata changed a substantive field.')
        statuses[mapping['status']] += 1
        expected[question['ID']] = after
        if question.get('KnowledgeGraph') != payload:
            data = (json.dumps(after, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            changes.append((record['path'], record['before'], data))
        record['question'] = after
    if require_complete and missing:
        raise GraphError(f'{len(missing)} installed questions have no source mapping; first: {missing[0]}.')
    if require_complete and statuses['unresolved']:
        raise GraphError(f'{statuses["unresolved"]} source mappings remain unresolved; complete their content review first.')
    bundle_changes = _bundle_changes(root, records) if refresh_browsers else []
    report = {'dryRun': dry_run, 'graphVersion': version, 'installedQuestions': len(records),
              'sourceMappings': len(mappings), 'boundMappings': len(expected), **statuses,
              'completedMappings': statuses['mapped'] + statuses['non_diagnostic'],
              'completeCoverage': not missing and statuses['unresolved'] == 0,
              'missingMappings': missing, 'changedQuestions': len(changes),
              'changedBundles': len(bundle_changes), 'nonGraphFieldsPreserved': True}
    if not dry_run:
        def verify():
            for record in records:
                question = expected.get(record['question']['ID'])
                if question is None:
                    continue
                actual = read_json(record['path'])
                if actual != question:
                    raise GraphError(f'{question["ID"]}: post-apply field-preservation verification failed.')
                _bound_payload(actual, mappings[question['ID']], version, root)
        _commit_changes(changes + bundle_changes, verify)
    return report


def refresh_browser_bundles(root=ROOT, *, dry_run=True):
    records = installed_questions(root)
    changes = _bundle_changes(root, records)
    if not dry_run:
        _commit_changes(changes)
    return {'dryRun': dry_run, 'installedQuestions': len(records), 'changedBundles': len(changes),
            'nonGraphFieldsPreserved': True}


def verify_mappings(root=ROOT, source_dir=None, *, require_complete=False, check_browsers=True):
    report = apply_mappings(root, source_dir, dry_run=True, refresh_browsers=check_browsers,
                            require_complete=require_complete)
    if report['changedQuestions'] or report['changedBundles']:
        raise GraphError(f'Graph metadata needs refreshing: {report["changedQuestions"]} questions and '
                         f'{report["changedBundles"]} browser bundles differ.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('apply', 'export', 'verify'))
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source-dir', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Validate and report without changing files (default).')
    mode.add_argument('--write', action='store_true', help='Apply the preflighted metadata changes.')
    parser.add_argument('--require-complete', action='store_true', help='Require mapped or non_diagnostic coverage for every installed question.')
    parser.add_argument('--no-browser', action='store_true', help='Only append or verify question JSON metadata.')
    args = parser.parse_args()
    try:
        if args.command == 'export':
            report = refresh_browser_bundles(args.root, dry_run=not args.write)
        elif args.command == 'verify':
            if args.write:
                parser.error('verify is read-only; omit --write.')
            report = verify_mappings(args.root, args.source_dir, require_complete=args.require_complete,
                                     check_browsers=not args.no_browser)
        else:
            report = apply_mappings(args.root, args.source_dir, dry_run=not args.write,
                                    refresh_browsers=not args.no_browser, require_complete=args.require_complete)
    except (GraphError, OSError, ValueError) as exc:
        parser.exit(1, f'Graph metadata not applied: {exc}\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
