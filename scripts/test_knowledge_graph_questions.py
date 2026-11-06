"""Graph append/export changes preserve authored questions and browser mathematics."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from export_amc_bank import browser_question
from import_question_bank import import_bank
from knowledge_graph import GraphError, build_database, context_for_question, question_fingerprint
import knowledge_graph_questions as integration
from question_banks import BankError, browser_bank


class QuestionMappingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.records = {}
        for folder, bank, question_id in (('cn-math-bank', 'cn-math', 'cnm_p006_q1'),
                                          ('amc-bank', 'amc', '2025_AMC_8_Q01'),
                                          ('custom-banks/example', 'example', 'example__add')):
            base = self.root / folder
            (base / 'questions').mkdir(parents=True)
            (base / 'figures').mkdir()
            question = {'ID': question_id, 'Bank': bank, 'SchemaVersion': '2.0',
                        'Question': r'What is \(2+2\)?', 'Choices': {}, 'Correct Answer': '4',
                        'ResponseType': 'numeric', 'Language': 'en', 'Level': 'Primary',
                        'Grade': 1, 'CurriculumUnit': 'Addition', 'Batch': 'add', 'Number': 1,
                        'Topic': {'id': 'add', 'label': 'Addition'}, 'domain': ['domain:number-algebra'],
                        'skill': ['skill:old:source'],
                        'Solution': 'Add two and two to get four.' if bank == 'example' else '',
                        'Meta': {'SolutionSource': 'Test source', 'Original': {'prompt': '二加二'},
                                 'Attribution': 'Test', 'License': 'CC0'}}
            self.write(base / 'questions' / (question_id + '.json'), question)
            if bank == 'example':
                self.write(base / 'bank.json', {'id': 'example', 'label': 'Example',
                           'attribution': 'Test', 'license': 'CC0'})
            self.records[question_id] = {'path': base / 'questions' / (question_id + '.json'),
                                         'question': question}
        self.write_bundles()
        self.source = {'metadata': {'version': 'test-graph-v1'},
                       'nodes': [{'id': 'cnm_p006'}, {'id': 'cnm_p001'}],
                       'relationships': [], 'mappings': []}
        for record in self.records.values():
            question = record['question']
            self.source['mappings'].append({
                'questionId': question['ID'], 'bank': question['Bank'],
                **question_fingerprint(question, root=self.root),
                'status': 'mapped', 'reviewStatus': 'machine_reviewed',
                'assessedIds': ['cnm_p006'], 'supportIds': ['cnm_p001'],
                'routes': [{'id': 'add', 'label': 'Add two quantities', 'nodeIds': ['cnm_p006']}],
                'flags': [], 'rationale': 'The displayed task asks for addition of two given numbers.',
                'answerCheck': {'status': 'checked', 'reason': '2+2=4'},
                'reviews': [{'reviewer': 'test-reviewer', 'decision': 'accepted'}]})
        self.source_patch = patch.object(integration, 'load_source', return_value=self.source)
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def write_bundles(self):
        for bank, folder, variable in (('cn-math', 'cn-math-bank', 'CN_MATH_BANK'),
                                        ('amc', 'amc-bank', 'AMC_BANK')):
            items = [{'id': record['question']['ID'], 'question': record['question']['Question'],
                      'choices': record['question']['Choices'], 'answer': record['question']['Correct Answer'],
                      'responseType': record['question']['ResponseType'], 'solution': 'Unchanged browser prose',
                      'extraBrowserMetadata': {'latex': r'\(x^2\)', 'figureSource': 'author'}}
                     for record in self.records.values() if record['question']['Bank'] == bank]
            payload = {'id': bank, 'extraBankMetadata': 'preserved', 'questions': items}
            (self.root / folder / 'bank.js').write_text(
                '/* Preserve this attribution. */\nwindow.' + variable + ' = '
                + json.dumps(payload, ensure_ascii=False) + ';\n', encoding='utf-8')
        question = self.records['example__add']['question']
        payload = [{'id': 'example', 'questions': [{'id': question['ID'], 'question': question['Question'],
                    'choices': {}, 'answer': '4', 'responseType': 'numeric', 'extraBrowserMetadata': 'kept'}]}]
        (self.root / 'custom-banks/banks.js').write_text(
            'window.CUSTOM_MATH_BANKS = ' + json.dumps(payload) + ';\n', encoding='utf-8')

    def snapshot(self):
        return {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}

    def build_graph_database(self):
        source = self.root / 'knowledge-graph/source'
        self.write(source / 'metadata.json', self.source['metadata'])
        self.write(source / 'nodes.json', [
            {'id': node['id'], 'name': node['id'], 'description': 'A test mathematical concept.',
             'kind': 'concept', 'reviewStatus': 'machine_reviewed', 'criteria': ['Identify a quantity'],
             'aliases': []} for node in self.source['nodes']])
        self.write(source / 'relationships.json', [])
        (source / 'mappings.jsonl').write_text(
            ''.join(json.dumps(mapping) + '\n' for mapping in self.source['mappings']), encoding='utf-8')
        build_database(root=self.root)

    def incoming_bank(self, question_id='newbank__add', review_status='user_asserted'):
        question = deepcopy(self.records['example__add']['question'])
        question.update(ID=question_id, Bank=question_id.split('__')[0])
        mapping = deepcopy(self.source['mappings'][-1])
        mapping.update(questionId=question['ID'], bank=question['Bank'], reviewStatus=review_status,
                       **question_fingerprint(question, root=self.root))
        question['KnowledgeGraph'] = integration.graph_payload(mapping, 'test-graph-v1')
        source = self.root / ('incoming-' + question['Bank'])
        self.write(source / 'bank.json', {'id': question['Bank'], 'label': 'Imported example',
                   'attribution': 'Test', 'license': 'CC0'})
        path = source / 'questions' / (question['ID'] + '.json')
        self.write(path, question)
        return source, path, question

    def test_apply_preflights_preserves_all_other_fields_and_is_idempotent(self):
        before = self.snapshot()
        report = integration.apply_mappings(self.root)
        self.assertEqual(report['boundMappings'], 3)
        self.assertEqual(report['changedQuestions'], 3)
        self.assertEqual(report['changedBundles'], 3)
        self.assertEqual(self.snapshot(), before)
        report = integration.apply_mappings(self.root, dry_run=False, require_complete=True)
        self.assertFalse(report['dryRun'])
        for record in self.records.values():
            actual = json.loads(record['path'].read_text(encoding='utf-8'))
            self.assertEqual(integration._without_graph(actual, 'KnowledgeGraph'), record['question'])
            self.assertEqual(actual['KnowledgeGraph']['version'], 'test-graph-v1')
            self.assertEqual(actual['KnowledgeGraph']['reviewStatus'], 'machine_reviewed')
            self.assertEqual(actual['KnowledgeGraph']['assessedIds'], ['cnm_p006'])
        after = self.snapshot()
        second = integration.apply_mappings(self.root, dry_run=False, require_complete=True)
        self.assertEqual((second['changedQuestions'], second['changedBundles']), (0, 0))
        self.assertEqual(self.snapshot(), after)
        self.assertEqual(integration.verify_mappings(self.root)['boundMappings'], 3)
        for path, original in before.items():
            if path.suffix != '.js':
                continue
            if path.name == 'bank.js':
                self.assertIn(b'Preserve this attribution', path.read_bytes())
            variable = 'CUSTOM_MATH_BANKS' if path.name == 'banks.js' else 'AMC_BANK' if 'amc-bank' in str(path) else 'CN_MATH_BANK'
            original_text = original.decode('utf-8')
            payload_before = json.loads(original_text.split('window.' + variable + ' = ')[1].strip().removesuffix(';'))
            _, _, payload_after, _ = integration._read_bundle(path, variable)
            banks_before = payload_before if isinstance(payload_before, list) else [payload_before]
            banks_after = payload_after if isinstance(payload_after, list) else [payload_after]
            for old_bank, new_bank in zip(banks_before, banks_after):
                self.assertEqual(integration._without_graph(old_bank, 'questions'), integration._without_graph(new_bank, 'questions'))
                for old, new in zip(old_bank['questions'], new_bank['questions']):
                    self.assertEqual(old, integration._without_graph(new, 'knowledgeGraph'))

    def test_stale_binding_invalid_id_and_duplicate_mapping_change_nothing(self):
        original = deepcopy(self.source['mappings'])
        for kind in ('hash', 'node', 'duplicate'):
            with self.subTest(kind=kind):
                self.source['mappings'] = deepcopy(original)
                if kind == 'hash':
                    self.source['mappings'][-1]['contentHash'] = '0' * 64
                elif kind == 'node':
                    self.source['mappings'][-1]['assessedIds'] = ['math:missing']
                else:
                    self.source['mappings'].append(deepcopy(original[0]))
                before = self.snapshot()
                with self.assertRaises(GraphError):
                    integration.apply_mappings(self.root, dry_run=False)
                self.assertEqual(self.snapshot(), before)

    def test_changed_or_missing_figure_invalidates_mapping_before_mutation(self):
        record = self.records['cnm_p006_q1']
        question = record['question']
        question['Question'] += '\n[Figure 1](figures/shape.svg)'
        image = record['path'].parent.parent / 'figures/shape.svg'
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
        self.write(record['path'], question)
        self.write_bundles()
        self.source['mappings'][0].update(question_fingerprint(question, root=self.root))
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path/></svg>', encoding='utf-8')
        before = self.snapshot()
        with self.assertRaisesRegex(GraphError, 'stale|figure'):
            integration.apply_mappings(self.root, dry_run=False)
        self.assertEqual(self.snapshot(), before)
        image.unlink()
        with self.assertRaises((GraphError, ValueError)):
            integration.apply_mappings(self.root, dry_run=False)

    def test_stale_browser_task_rejects_entire_apply(self):
        path = self.root / 'amc-bank/bank.js'
        path.write_text(path.read_text().replace('What is', 'Find instead'), encoding='utf-8')
        before = self.snapshot()
        with self.assertRaisesRegex(GraphError, 'browser question differs'):
            integration.apply_mappings(self.root, dry_run=False)
        self.assertEqual(self.snapshot(), before)

    def test_complete_accounting_does_not_report_unresolved_as_mapped(self):
        mapping = self.source['mappings'][-1]
        mapping.update(status='unresolved', assessedIds=[], supportIds=[], routes=[],
                       flags=['ambiguous-task'], rationale='Explicit unresolved test case.')
        report = integration.apply_mappings(self.root, dry_run=False)
        self.assertEqual((report['mapped'], report['unresolved']), (2, 1))
        self.assertEqual(report['completedMappings'], 2)
        self.assertFalse(report['completeCoverage'])
        self.assertEqual(report['missingMappings'], [])
        with self.assertRaisesRegex(GraphError, 'remain unresolved'):
            integration.apply_mappings(self.root, require_complete=True)
        self.source['mappings'].pop()
        with self.assertRaisesRegex(GraphError, 'no source mapping'):
            integration.apply_mappings(self.root, require_complete=True)

    def test_non_diagnostic_append_export_import_and_complete_coverage_preserve_fields(self):
        record = self.records['example__add']
        record['question']['Question'] = 'The result has the same count, 4. What is the resulting count?'
        self.write(record['path'], record['question'])
        self.write_bundles()
        mapping = self.source['mappings'][-1]
        mapping.update(status='non_diagnostic', assessedIds=[], supportIds=[], routes=[],
                       contextualIds=['cnm_p006'], flags=['answer_relation_supplied'],
                       rationale='The count is supplied; addition is contextual and is not assessed.',
                       **question_fingerprint(record['question'], root=self.root))
        before = deepcopy(record['question'])
        report = integration.apply_mappings(self.root, dry_run=False, require_complete=True)
        self.assertEqual((report['mapped'], report['non_diagnostic'], report['unresolved']), (2, 1, 0))
        self.assertEqual(report['completedMappings'], 3)
        self.assertTrue(report['completeCoverage'])
        actual = integration.read_json(record['path'])
        self.assertEqual({k: v for k, v in actual.items() if k != 'KnowledgeGraph'}, before)
        self.assertEqual(actual['KnowledgeGraph']['contextualIds'], ['cnm_p006'])
        self.assertNotIn('gradingStatus', actual['KnowledgeGraph'])
        manifest = integration.read_json(self.root / 'custom-banks/example/bank.json')
        self.assertEqual(browser_bank(manifest, [actual])['questions'][0]['knowledgeGraph'],
                         actual['KnowledgeGraph'])
        integration.verify_mappings(self.root, require_complete=True)
        self.build_graph_database()
        integration.validate_imported_references(actual, root=self.root)
        self.assertEqual(actual['KnowledgeGraph']['reviewStatus'], 'machine_reviewed')
        source, path, incoming = self.incoming_bank()
        import_bank(source, root=self.root)
        installed = integration.read_json(self.root / 'custom-banks/newbank/questions' / path.name)
        self.assertEqual(installed['KnowledgeGraph']['contextualIds'], ['cnm_p006'])
        self.assertEqual(installed['KnowledgeGraph']['reviewStatus'], 'user_asserted')
        self.assertEqual(context_for_question(installed, root=self.root)['status'], 'missing')

    def test_non_diagnostic_cannot_be_imported_with_missing_or_unknown_context(self):
        self.build_graph_database()
        _, _, question = self.incoming_bank()
        question['KnowledgeGraph'].update(status='non_diagnostic', assessedIds=[], supportIds=[], routes=[])
        for ids in (None, [], ['math:missing']):
            candidate = deepcopy(question)
            if ids is not None:
                candidate['KnowledgeGraph']['contextualIds'] = ids
            with self.subTest(contextualIds=ids), self.assertRaises(GraphError):
                integration.validate_imported_references(candidate, root=self.root)

    def test_route_only_complete_coverage_append_export_and_import_preserve_fields(self):
        for mapping in self.source['mappings']:
            mapping.update(assessedIds=[], routes=[
                {'id': 'combine', 'label': 'Combine the two quantities', 'nodeIds': ['cnm_p006']},
                {'id': 'count', 'label': 'Count the objects', 'nodeIds': ['cnm_p001']}])
        self.build_graph_database()
        before = {qid: deepcopy(record['question']) for qid, record in self.records.items()}
        report = integration.apply_mappings(self.root, dry_run=False, require_complete=True)
        self.assertEqual((report['mapped'], report['completedMappings']), (3, 3))
        self.assertTrue(report['completeCoverage'])
        for mapping in self.source['mappings']:
            qid = mapping['questionId']
            actual = integration.read_json(self.records[qid]['path'])
            self.assertEqual(integration._without_graph(actual, 'KnowledgeGraph'), before[qid])
            self.assertEqual(actual['KnowledgeGraph']['assessedIds'], [])
            self.assertEqual(actual['KnowledgeGraph']['routes'], mapping['routes'])
            context = context_for_question(actual, root=self.root)
            self.assertEqual(context['status'], 'mapped')
            self.assertEqual(context['routes'], mapping['routes'])
            self.assertEqual(context['assessedIds'], [])
            projection = browser_question(actual) if actual['Bank'] == 'amc' else browser_bank(
                {'id': actual['Bank'], 'label': 'Fixture', 'attribution': 'Fixture', 'license': 'CC0'},
                [actual])['questions'][0]
            self.assertEqual(projection['knowledgeGraph'], actual['KnowledgeGraph'])
        integration.verify_mappings(self.root, require_complete=True)
        snapshot = self.snapshot()
        again = integration.apply_mappings(self.root, dry_run=False, require_complete=True)
        self.assertEqual((again['changedQuestions'], again['changedBundles']), (0, 0))
        self.assertEqual(self.snapshot(), snapshot)
        source, _, _ = self.incoming_bank('example__add', review_status='machine_reviewed')
        import_bank(source, root=self.root, replace=True)
        central = integration.read_json(self.records['example__add']['path'])
        self.assertEqual(central['KnowledgeGraph']['reviewStatus'], 'machine_reviewed')
        self.assertEqual(context_for_question(central, root=self.root)['status'], 'mapped')
        source, path, incoming = self.incoming_bank()
        import_bank(source, root=self.root)
        installed = integration.read_json(self.root / 'custom-banks/newbank/questions' / path.name)
        self.assertEqual(integration._without_graph(installed, 'KnowledgeGraph'),
                         integration._without_graph(incoming, 'KnowledgeGraph'))
        self.assertEqual(installed['KnowledgeGraph']['assessedIds'], [])
        self.assertEqual(installed['KnowledgeGraph']['reviewStatus'], 'user_asserted')
        self.assertEqual(context_for_question(installed, root=self.root)['status'], 'missing')

    def test_route_only_import_rejects_missing_empty_unknown_or_non_diagnostic_routes(self):
        mapping = self.source['mappings'][-1]
        mapping['assessedIds'] = []
        self.build_graph_database()
        source, path, question = self.incoming_bank()
        variants = [dict(routes=[]),
                    dict(routes=[{'id': 'empty', 'label': 'Incomplete', 'nodeIds': []}]),
                    dict(routes=[{'id': 'unknown', 'label': 'Unknown', 'nodeIds': ['math:missing']}]),
                    dict(status='non_diagnostic', contextualIds=['cnm_p006'])]
        for changed in variants:
            incoming = deepcopy(question)
            incoming['KnowledgeGraph'].update(changed)
            self.write(path, incoming)
            before = self.snapshot()
            with self.subTest(changed=changed), self.assertRaises(BankError):
                import_bank(source, root=self.root)
            self.assertEqual(self.snapshot(), before)

    def test_write_failure_restores_original_question_bytes(self):
        before = self.snapshot()
        actual_write, calls = integration._atomic_bytes, []
        def fail_second(path, data):
            calls.append(path)
            if len(calls) == 2:
                raise OSError('simulated write failure')
            actual_write(path, data)
        with patch.object(integration, '_atomic_bytes', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated'):
                integration.apply_mappings(self.root, dry_run=False)
        self.assertEqual(self.snapshot(), before)

    def test_normal_export_projections_preserve_graph_stub(self):
        question = deepcopy(self.records['2025_AMC_8_Q01']['question'])
        question['KnowledgeGraph'] = integration.graph_payload(self.source['mappings'][1], 'test-graph-v1')
        self.assertEqual(browser_question(question)['knowledgeGraph'], question['KnowledgeGraph'])
        question = deepcopy(self.records['example__add']['question'])
        question['KnowledgeGraph'] = integration.graph_payload(self.source['mappings'][-1], 'test-graph-v1')
        manifest = {'id': 'example', 'label': 'Example', 'attribution': 'Test', 'license': 'CC0'}
        self.assertEqual(browser_bank(manifest, [question])['questions'][0]['knowledgeGraph'], question['KnowledgeGraph'])

    def test_import_valid_user_asserted_references_keeps_them_unreviewed(self):
        self.build_graph_database()
        source, _, question = self.incoming_bank()
        import_bank(source, root=self.root)
        installed = json.loads((self.root / 'custom-banks/newbank/questions/newbank__add.json').read_text(encoding='utf-8'))
        self.assertEqual(installed, question)
        self.assertEqual(installed['KnowledgeGraph']['reviewStatus'], 'user_asserted')
        self.assertEqual(context_for_question(installed, root=self.root)['status'], 'missing')
        bundle = integration._read_bundle(self.root / 'custom-banks/banks.js', 'CUSTOM_MATH_BANKS')[2]
        imported = next(bank for bank in bundle if bank['id'] == 'newbank')
        self.assertEqual(imported['questions'][0]['knowledgeGraph'], question['KnowledgeGraph'])

    def test_exact_central_mapping_reimport_retains_recorded_review_provenance(self):
        self.build_graph_database()
        source, path, question = self.incoming_bank('example__add', review_status='machine_reviewed')
        import_bank(source, root=self.root, replace=True)
        installed = json.loads(self.records['example__add']['path'].read_text(encoding='utf-8'))
        self.assertEqual(installed['KnowledgeGraph']['reviewStatus'], 'machine_reviewed')
        question['KnowledgeGraph']['reviewStatus'] = 'teacher_reviewed'
        self.write(path, question)
        before = self.snapshot()
        with self.assertRaisesRegex(BankError, 'user_asserted'):
            import_bank(source, root=self.root, replace=True)
        self.assertEqual(self.snapshot(), before)

    def test_import_invalid_reference_or_binding_is_rejected_before_install(self):
        self.build_graph_database()
        source, path, question = self.incoming_bank()
        for kind in ('unknown-node', 'stale-hash', 'false-review'):
            with self.subTest(kind=kind):
                changed = deepcopy(question)
                if kind == 'unknown-node':
                    changed['KnowledgeGraph']['assessedIds'] = ['math:absent']
                elif kind == 'stale-hash':
                    changed['Question'] = 'What is 3 + 4?'
                else:
                    changed['KnowledgeGraph']['reviewStatus'] = 'machine_reviewed'
                self.write(path, changed)
                before = self.snapshot()
                with self.assertRaises(BankError):
                    import_bank(source, root=self.root)
                self.assertEqual(self.snapshot(), before)

    def test_missing_graph_only_blocks_explicit_references(self):
        source, path, question = self.incoming_bank()
        with self.assertRaisesRegex(BankError, 'central graph database'):
            import_bank(source, root=self.root, check=True)
        question.pop('KnowledgeGraph')
        self.write(path, question)
        self.assertEqual(import_bank(source, root=self.root, check=True)['questions'], 1)

    def test_confirmed_notice_changes_only_appended_graph_metadata(self):
        for status in ('ambiguous', 'disagrees', 'matches'):
            self.assertNotIn('gradingStatus', integration.graph_payload(
                {**self.source['mappings'][0], 'answerCheck': {'status': status}}, 'test-graph-v1'))
        self.source['mappings'][0]['answerCheck'] = {'status': 'confirmed_ambiguous'}
        original = deepcopy(self.records['cnm_p006_q1']['question'])
        integration.apply_mappings(self.root, dry_run=False)
        installed = json.loads(self.records['cnm_p006_q1']['path'].read_text(encoding='utf-8'))
        self.assertEqual(integration._without_graph(installed, 'KnowledgeGraph'), original)
        self.assertNotIn('GradingStatus', installed)
        self.assertEqual(installed['Correct Answer'], '4')
        self.assertEqual(installed['KnowledgeGraph']['gradingStatus'], 'disputed')
        bank = integration._read_bundle(self.root / 'cn-math-bank/bank.js', 'CN_MATH_BANK')[2]
        self.assertEqual(bank['questions'][0]['knowledgeGraph'], installed['KnowledgeGraph'])

    def test_exact_central_import_refreshes_controlled_notice(self):
        self.source['mappings'][-1]['answerCheck'] = {'status': 'confirmed_conflict'}
        self.build_graph_database()
        source, path, question = self.incoming_bank('example__add', review_status='machine_reviewed')
        question['KnowledgeGraph'].pop('gradingStatus')
        question['KnowledgeGraph'].pop('gradingNote')
        self.write(path, question)
        import_bank(source, root=self.root, replace=True)
        installed = json.loads(self.records['example__add']['path'].read_text(encoding='utf-8'))
        self.assertEqual(installed['KnowledgeGraph']['gradingStatus'], 'disputed')
        self.assertIn('answer key', installed['KnowledgeGraph']['gradingNote'])
        self.assertEqual(integration._without_graph(installed, 'KnowledgeGraph'),
                         integration._without_graph(question, 'KnowledgeGraph'))

    def test_user_asserted_import_cannot_supply_controlled_grading_notice(self):
        self.build_graph_database()
        source, path, question = self.incoming_bank()
        question['KnowledgeGraph'].update(gradingStatus='disputed', gradingNote='An unsupported claim.')
        self.write(path, question)
        with self.assertRaisesRegex(BankError, 'grading notices must come from an exact central mapping'):
            import_bank(source, root=self.root)


if __name__ == '__main__':
    unittest.main()
