"""Exercise portable bank imports and their runtime boundary in temporary folders."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request

from connection_settings import ConnectionSettings
from import_question_bank import import_bank
from practice_tutor import question_images, review_submission
from question_banks import BankError, bank_root_for_question, custom_question_path
from serve_math_practice import Handler, ThreadingHTTPServer
from student_assessment import AssessmentError, ModelConfig, StudentAssessment


ROOT = Path(__file__).resolve().parents[1]
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><path d="M0 0L10 10"/></svg>'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class BankFixture:
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.root = self.directory / 'app'
        self.root.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def make_bank(self, bank_id='algebra', figure=None):
        source = self.directory / ('source-' + bank_id)
        (source / 'questions').mkdir(parents=True)
        (source / 'figures').mkdir()
        manifest = {'id': bank_id, 'label': 'Original algebra practice',
                    'attribution': 'Test author', 'license': 'CC0-1.0'}
        record = {'ID': bank_id + '__addition', 'Bank': bank_id, 'SchemaVersion': '2.0',
                  'ResponseType': 'numeric', 'Language': 'en', 'Level': 'Middle school',
                  'Grade': 7, 'CurriculumUnit': 'Algebra', 'Batch': 'addition', 'Number': 1,
                  'Topic': {'id': 'addition', 'label': 'Addition'},
                  'Question': 'What is 2 + 2?', 'Choices': {}, 'Correct Answer': '4',
                  'Solution': 'Add two and two to get four.',
                  'domain': ['domain:number-algebra'], 'skill': ['skill:arithmetic:add'],
                  'Meta': {'Attribution': 'Test author', 'License': 'CC0-1.0',
                           'SolutionSource': 'Original worked solution'}}
        if figure:
            record['Question'] += '\n[Figure 1](figures/' + figure + ')'
            (source / 'figures' / figure).write_bytes(PNG if figure.endswith('.png') else SVG)
        self.write_json(source / 'bank.json', manifest)
        self.write_json(source / 'questions' / (record['ID'] + '.json'), record)
        return source, record

    def make_amc_question(self, question_id='2021_Fall_AMC_10A_Q01', figure=False):
        bank = self.root / 'amc-bank'
        (bank / 'questions').mkdir(parents=True, exist_ok=True)
        record = {'ID': question_id, 'Bank': 'amc', 'ResponseType': 'choice',
                  'Question': 'What is 2 + 2?', 'Choices': {'A': '3', 'B': '4'},
                  'Correct Answer': 'B', 'Solution': ''}
        if figure:
            (bank / 'figures').mkdir(exist_ok=True)
            (bank / 'figures/shape.png').write_bytes(PNG)
            record['Question'] += '\n[Figure 1](figures/shape.png)'
            record['Choices']['B'] = '[Figure 2](figures/shape.png)'
        self.write_question(bank, record)
        return bank, record

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def write_question(self, source, record, filename=None):
        self.write_json(source / 'questions' / (filename or record['ID'] + '.json'), record)

    def bundle(self):
        value = (self.root / 'custom-banks/banks.js').read_text(encoding='utf-8')
        return json.loads(value.removeprefix('window.CUSTOM_MATH_BANKS = ').rstrip().removesuffix(';'))


class ImportTests(BankFixture, unittest.TestCase):
    def test_shipped_example_validates_without_installing(self):
        result = import_bank(ROOT / 'question-bank-template/example', root=self.root, check=True)
        self.assertEqual(result, {'id': 'example', 'questions': 4, 'figures': 1})
        self.assertFalse((self.root / 'custom-banks').exists())

    def test_install_copies_questions_and_only_referenced_figures(self):
        source, record = self.make_bank(figure='shape.svg')
        (source / 'figures/unreferenced.svg').write_bytes(SVG)
        (source / 'private-notes.txt').write_text('not a public asset', encoding='utf-8')
        original = (source / 'questions' / (record['ID'] + '.json')).read_bytes()
        self.assertEqual(import_bank(source, root=self.root), {'id': 'algebra', 'questions': 1, 'figures': 1})
        installed = self.root / 'custom-banks/algebra'
        self.assertEqual(json.loads((installed / 'questions' / (record['ID'] + '.json')).read_text()), record)
        self.assertEqual((installed / 'figures/shape.svg').read_bytes(), SVG)
        self.assertFalse((installed / 'figures/unreferenced.svg').exists())
        self.assertFalse((installed / 'private-notes.txt').exists())
        self.assertEqual((source / 'questions' / (record['ID'] + '.json')).read_bytes(), original)
        browser = self.bundle()[0]
        self.assertEqual(browser['id'], 'algebra')
        self.assertEqual(browser['figuresBase'], '../custom-banks/algebra/figures/')
        self.assertEqual(browser['questions'][0]['id'], record['ID'])
        self.assertEqual(browser['questions'][0]['answer'], record['Correct Answer'])
        self.assertEqual(browser['questions'][0]['solution'], record['Solution'])

    def test_multiple_banks_and_replacement_preserve_other_content(self):
        chinese = self.root / 'cn-math-bank/questions'
        chinese.mkdir(parents=True)
        (chinese / 'cnm_p001_q1.json').write_bytes(b'original built-in question')
        source, record = self.make_bank(figure='old.svg')
        second, _ = self.make_bank('geometry')
        import_bank(source, root=self.root)
        import_bank(second, root=self.root)
        other_path = self.root / 'custom-banks/geometry/questions/geometry__addition.json'
        other_before = other_path.read_bytes()
        before = (self.root / 'custom-banks/banks.js').read_bytes()
        with self.assertRaisesRegex(BankError, 'already installed'):
            import_bank(source, root=self.root)
        self.assertEqual((self.root / 'custom-banks/banks.js').read_bytes(), before)
        record['Question'] = 'What is 3 + 3?'
        record['Correct Answer'] = '6'
        record['Solution'] = 'Add three and three.'
        self.write_question(source, record)
        import_bank(source, root=self.root, replace=True)
        banks = self.bundle()
        self.assertEqual([bank['id'] for bank in banks], ['algebra', 'geometry'])
        self.assertEqual(banks[0]['questions'][0]['answer'], '6')
        self.assertFalse((self.root / 'custom-banks/algebra/figures/old.svg').exists())
        self.assertEqual(other_path.read_bytes(), other_before)
        self.assertEqual((chinese / 'cnm_p001_q1.json').read_bytes(), b'original built-in question')
        self.assertFalse(any(path.name.startswith(('.import-', '.previous-'))
                             for path in (self.root / 'custom-banks').iterdir()))

    def test_invalid_replacement_keeps_installed_bank_and_bundle(self):
        source, record = self.make_bank()
        import_bank(source, root=self.root)
        installed = self.root / 'custom-banks/algebra/questions/algebra__addition.json'
        before = installed.read_bytes(), (self.root / 'custom-banks/banks.js').read_bytes()
        record['Correct Answer'] = 'four metres'
        self.write_question(source, record)
        with self.assertRaises(BankError):
            import_bank(source, root=self.root, replace=True)
        self.assertEqual((installed.read_bytes(), (self.root / 'custom-banks/banks.js').read_bytes()), before)

    def test_bank_and_question_ids_cannot_alias_other_banks_or_paths(self):
        source, original = self.make_bank()
        manifest = json.loads((source / 'bank.json').read_text())
        for bank_id in ('cn-math', '../algebra', 'Uppercase', 'double__underscore', 'a' * 49):
            with self.subTest(bank_id=bank_id):
                self.write_json(source / 'bank.json', {**manifest, 'id': bank_id})
                with self.assertRaises(BankError):
                    import_bank(source, root=self.root)
        self.write_json(source / 'bank.json', manifest)
        for changes in ({'ID': 'other__addition'}, {'ID': '../algebra__addition'},
                        {'ID': 'algebra__'}, {'ID': 'algebra__different_filename'},
                        {'Bank': 'other'}, {'SchemaVersion': '1.0'}):
            with self.subTest(changes=changes):
                self.write_question(source, {**original, **changes}, filename=original['ID'] + '.json')
                with self.assertRaises(BankError):
                    import_bank(source, root=self.root)
        self.assertFalse((self.root / 'custom-banks').exists())
        for question_id in ('../algebra__addition', 'algebra__../addition', 'other__addition', None):
            self.assertIsNone(custom_question_path(question_id, self.root))

    def test_invalid_answers_and_choices_are_rejected(self):
        source, original = self.make_bank()
        cases = [
            {'ResponseType': 'choice', 'Choices': {'A': 'One', 'B': 'Two'}, 'Correct Answer': 'C'},
            {'ResponseType': 'choice', 'Choices': {'A': '', 'B': 'Two'}, 'Correct Answer': 'A'},
            {'ResponseType': 'choice', 'Choices': {'A': 'One'}, 'Correct Answer': 'A'},
            {'ResponseType': 'choice', 'Choices': {'A': 'One', 'F': 'Six'}, 'Correct Answer': 'A'},
            {'Choices': {'A': 'Four'}}, {'Correct Answer': r'\(4\)'},
            {'Correct Answer': '4 cm'}, {'Accepted Answers': ['four']},
            {'ResponseType': 'short', 'Accepted Answers': ['four'], 'Rejected Answers': [' FOUR ']},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                self.write_question(source, {**original, **changes})
                with self.assertRaises(BankError):
                    import_bank(source, root=self.root, check=True)

    def test_missing_and_escaping_figures_are_rejected_before_install(self):
        source, original = self.make_bank(figure='shape.svg')
        (source / 'outside.svg').write_bytes(SVG)
        for relative in ('figures/missing.svg', '../outside.svg', 'figures/../outside.svg',
                         'figures/nested/shape.svg', 'https://example.test/shape.svg',
                         'figures\\shape.svg'):
            with self.subTest(relative=relative):
                record = {**original, 'Question': '[Figure 1](' + relative + ')'}
                self.write_question(source, record)
                with self.assertRaises(BankError):
                    import_bank(source, root=self.root)
        self.assertFalse((self.root / 'custom-banks').exists())

    def test_active_or_external_svg_and_mislabeled_raster_are_rejected(self):
        source, record = self.make_bank(figure='shape.svg')
        for body in (b'<script>alert(1)</script>', b'<path onclick="alert(1)"/>',
                     b'<image href="https://example.test/image.png"/>',
                     b'<foreignObject><div>HTML</div></foreignObject>',
                     b'<animate attributeName="x"/>',
                     b'<style>path{fill:url(https://example.test/paint)}</style>'):
            with self.subTest(body=body):
                (source / 'figures/shape.svg').write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg">' + body + b'</svg>')
                with self.assertRaises(BankError):
                    import_bank(source, root=self.root, check=True)
        record['Question'] = '[Figure 1](figures/shape.png)'
        self.write_question(source, record)
        (source / 'figures/shape.png').write_bytes(SVG)
        with self.assertRaises(BankError):
            import_bank(source, root=self.root, check=True)

    def test_problem_number_and_topic_labels_are_consistent(self):
        source, original = self.make_bank()
        second = {**copy.deepcopy(original), 'ID': 'algebra__second'}
        for changes in ({}, {'Number': 2, 'CurriculumUnit': 'Other unit'},
                        {'Number': 2, 'Topic': {'id': 'addition', 'label': 'Other topic'}}):
            with self.subTest(changes=changes):
                self.write_question(source, {**second, **changes})
                with self.assertRaises(BankError):
                    import_bank(source, root=self.root, check=True)


class CustomRuntimeTests(BankFixture, unittest.TestCase):
    def test_installed_question_is_authoritative_without_model_calls(self):
        source, record = self.make_bank()
        import_bank(source, root=self.root)
        assessor = StudentAssessment(ModelConfig(), root=self.root)
        forged = {'questionId': record['ID'], 'answer': '4', 'thoughts': 'I added two and two.',
                  'question': {'Correct Answer': '999'}, 'Correct Answer': '999', 'solution': 'Use 999.'}
        with patch('student_assessment.OPENER.open', side_effect=AssertionError('No model request expected')):
            result = assessor.assess(forged)
            wrong = assessor.assess({**forged, 'answer': '999'})
        self.assertEqual(result['answerCategory'], 'correct')
        self.assertTrue(result['answerCorrect'])
        self.assertEqual(wrong['answerCategory'], 'wrong')
        self.assertFalse(result['modelUsed'])
        self.assertEqual(result['decisionRequests'], 0)
        self.assertEqual(result['category'], 'cannot_judge')
        self.assertEqual(assessor._question(record['ID']), record)

    def test_missing_or_mismatched_custom_question_does_not_fall_back_to_model(self):
        source, record = self.make_bank()
        import_bank(source, root=self.root)
        assessor = StudentAssessment(ModelConfig(('https://decision.example',), 'test-model'), root=self.root)
        with patch.object(assessor, '_decide', side_effect=AssertionError('No model fallback expected')):
            for question_id in ('algebra__missing', 'uninstalled__addition', '../algebra__addition'):
                with self.subTest(question_id=question_id), self.assertRaises(AssessmentError):
                    assessor.assess({'questionId': question_id, 'answer': '4', 'thoughts': 'I added.'})
            installed = self.root / 'custom-banks/algebra/questions/algebra__addition.json'
            self.write_json(installed, {**record, 'Bank': 'other'})
            with self.assertRaisesRegex(AssessmentError, 'does not match'):
                assessor.assess({'questionId': record['ID'], 'answer': '4', 'thoughts': 'I added.'})

    def test_custom_diagram_resolution_uses_installed_bank_and_deduplicates(self):
        source, record = self.make_bank(figure='shape.png')
        record['Solution'] += '\n[Figure 2](figures/shape.png)'
        self.write_question(source, record)
        import_bank(source, root=self.root)
        renderer = MagicMock()
        page = renderer.open.return_value.__enter__.return_value.__getitem__.return_value
        page.rect.width, page.rect.height = 10, 10
        page.get_pixmap.return_value.tobytes.return_value = PNG
        with patch.dict('sys.modules', {'pymupdf': renderer}):
            urls, names = question_images(record, root=self.root)
        self.assertEqual(names, ['figures/shape.png'])
        self.assertEqual(urls, ['data:image/png;base64,' + base64.b64encode(PNG).decode('ascii')])
        renderer.open.assert_called_once_with(self.root / 'custom-banks/algebra/figures/shape.png')
        with self.assertRaises(AssessmentError):
            question_images({**record, 'Question': '[Figure 1](figures/../../private.png)', 'Solution': ''}, root=self.root)

    def test_tutor_uses_assessors_root_for_custom_figures(self):
        source, record = self.make_bank()
        import_bank(source, root=self.root)
        assessor = StudentAssessment(ModelConfig(), root=self.root)
        settings = ConnectionSettings(self.root / 'config.json')
        settings.save({'inference': {'provider': 'api', 'bases': ['https://inference.example'], 'model': 'test-model'}})
        reply = {'choices': [{'message': {'content': json.dumps({'category': 'correct', 'answerCategory': 'correct',
                                                                 'coach': 'Your explanation is correct.', 'hint': ''})}}]}
        attempt = {'questionId': record['ID'], 'answer': '4', 'thoughts': 'I added two and two.',
                   'category': 'cannot_judge', 'answerCategory': 'correct'}
        with patch('practice_tutor.question_images', return_value=([], [])) as images, \
             patch('practice_tutor.request', return_value=reply):
            result = review_submission(assessor, settings, MagicMock(), attempt)
        self.assertTrue(result['answerCorrect'])
        images.assert_called_once_with(record, root=self.root)


class AmcRuntimeTests(BankFixture, unittest.TestCase):
    def test_historical_and_current_ids_use_authoritative_records_without_models(self):
        assessor = StudentAssessment(ModelConfig(), root=self.root)
        ids = ('1950_AMC_12_Q50', '1985_AMC_8_Q25', '2000_AMC_10_Q25',
               '2025_AMC_10A_Q01', '2025_AMC_10B_Q25', '2025_AMC_12A_Q01',
               '2025_AMC_12B_Q25', '2021_Fall_AMC_10A_Q01', '2021_Fall_AMC_12B_Q25')
        with patch('student_assessment.OPENER.open', side_effect=AssertionError('No model request expected')):
            for question_id in ids:
                with self.subTest(question_id=question_id):
                    _, record = self.make_amc_question(question_id)
                    attempt = {'questionId': question_id, 'answer': 'B', 'thoughts': 'I added two and two.',
                               'question': {'Correct Answer': 'A'}, 'Correct Answer': 'A'}
                    result = assessor.assess(attempt)
                    wrong = assessor.assess({**attempt, 'answer': 'A'})
                    self.assertTrue(result['answerCorrect'])
                    self.assertFalse(wrong['answerCorrect'])
                    self.assertEqual(result['category'], 'cannot_judge')
                    self.assertFalse(result['modelUsed'])
                    self.assertEqual(result['decisionRequests'], 0)
                    self.assertEqual(assessor._question(question_id), record)

    def test_invalid_missing_and_mismatched_amc_records_do_not_use_models(self):
        bank, record = self.make_amc_question()
        assessor = StudentAssessment(ModelConfig(('https://decision.example',), 'test-model'), root=self.root)
        with patch.object(assessor, '_decide', side_effect=AssertionError('No model fallback expected')):
            for question_id, status in (('9999_AMC_8_Q01', 404), ('1950_AMC_12_Q51', 400),
                                        ('2025_AMC_8_Q00', 400), ('2025_AMC_8_Q1', 400),
                                        ('../2025_AMC_8_Q01', 400)):
                with self.subTest(question_id=question_id), self.assertRaises(AssessmentError) as raised:
                    assessor.assess({'questionId': question_id, 'answer': 'B', 'thoughts': 'I added.'})
                self.assertEqual(raised.exception.status, status)
            for changes in ({'ID': '2025_AMC_8_Q01'}, {'Bank': 'other'}):
                self.write_question(bank, {**record, **changes}, filename=record['ID'] + '.json')
                with self.assertRaisesRegex(AssessmentError, 'does not match'):
                    assessor._question(record['ID'])

    def test_configured_amc_assessment_uses_decision_model_with_disk_reference(self):
        _, record = self.make_amc_question()
        assessor = StudentAssessment(ModelConfig(('https://decision.example',), 'test-model'), root=self.root)
        with patch.object(assessor, '_decide', return_value=[{'id': 'correctness', 'code': 'correct'}]) as decide:
            result = assessor.assess({'questionId': record['ID'], 'answer': 'B', 'thoughts': 'I added.'})
        self.assertTrue(result['answerCorrect'])
        self.assertTrue(result['modelUsed'])
        self.assertEqual(result['decisionRequests'], 1)
        self.assertIn('"referenceAnswer": "B"', decide.call_args.args[0])
        self.assertIn('"referenceSolution": ""', decide.call_args.args[0])

    def test_amc_tutor_figures_use_amc_bank_and_deduplicate_picture_choices(self):
        bank, record = self.make_amc_question(figure=True)
        renderer = MagicMock()
        page = renderer.open.return_value.__enter__.return_value.__getitem__.return_value
        page.rect.width, page.rect.height = 10, 10
        page.get_pixmap.return_value.tobytes.return_value = PNG
        with patch.dict('sys.modules', {'pymupdf': renderer}):
            urls, names = question_images(record, root=self.root)
        self.assertEqual(bank_root_for_question(record, root=self.root), bank)
        self.assertEqual(names, ['figures/shape.png'])
        self.assertEqual(urls, ['data:image/png;base64,' + base64.b64encode(PNG).decode('ascii')])
        renderer.open.assert_called_once_with(bank / 'figures/shape.png')
        with self.assertRaises(AssessmentError):
            question_images({**record, 'Question': '[Figure 1](figures/../../config.json)'}, root=self.root)
        with self.assertRaises(BankError):
            bank_root_for_question({**record, 'ID': 'other__question'}, root=self.root)


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class CustomAssetHttpTests(BankFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.root_patch = patch('serve_math_practice.ROOT', self.root)
        self.root_patch.start()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()
        self.root_patch.stop()
        super().tearDown()

    def request(self, path):
        try:
            with self.opener.open(self.base + path, timeout=5) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.headers, exc.read()

    def test_bundle_route_works_before_and_after_import(self):
        code, headers, data = self.request('/custom-banks/banks.js')
        self.assertEqual(code, 200)
        self.assertEqual(data, b'window.CUSTOM_MATH_BANKS = [];\n')
        self.assertIn('javascript', headers['Content-Type'])
        source, _ = self.make_bank(figure='shape.svg')
        import_bank(source, root=self.root)
        code, _, data = self.request('/custom-banks/banks.js')
        self.assertEqual(code, 200)
        self.assertEqual(data, (self.root / 'custom-banks/banks.js').read_bytes())
        code, headers, data = self.request('/custom-banks/algebra/figures/shape.svg')
        self.assertEqual(code, 200)
        self.assertEqual(data, SVG)
        self.assertEqual(headers['Content-Type'], 'image/svg+xml')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn('sandbox', headers['Content-Security-Policy'])

    def test_private_bank_files_and_path_traversal_are_not_public(self):
        source, _ = self.make_bank(figure='shape.svg')
        import_bank(source, root=self.root)
        bank = self.root / 'custom-banks/algebra'
        (bank / 'config.json').write_text('{"secret":"private"}', encoding='utf-8')
        (self.root / 'config.json').write_text('{"secret":"root-private"}', encoding='utf-8')
        for path in ('/custom-banks/algebra/bank.json', '/custom-banks/algebra/config.json',
                     '/custom-banks/algebra/questions/algebra__addition.json', '/custom-banks/config.json',
                     '/custom-banks/algebra/figures/../config.json',
                     '/custom-banks/algebra/figures/%2e%2e/config.json',
                     '/custom-banks/algebra/figures/%2e%2e%2fconfig.json',
                     '/custom-banks/algebra/figures/..%5cconfig.json',
                     '/custom-banks/algebra/figures/../../../config.json',
                     '/custom-banks/algebra/figures/shape.svg/extra',
                     '/custom-banks/uninstalled/figures/shape.svg'):
            with self.subTest(path=path):
                code, _, data = self.request(path)
                self.assertEqual(code, 404)
                self.assertNotIn(b'private', data)

    def test_amc_bundle_and_flat_figures_are_public_but_other_files_are_private(self):
        bank, record = self.make_amc_question(figure=True)
        bundle = b'window.AMC_BANK = {"questions": []};\n'
        (bank / 'bank.js').write_bytes(bundle)
        (bank / 'figures/shape.svg').write_bytes(SVG)
        (bank / 'figures/config.json').write_text('{"secret":"private"}', encoding='utf-8')
        (bank / 'config.json').write_text('{"secret":"private"}', encoding='utf-8')
        (bank / 'figures/nested').mkdir()
        (bank / 'figures/nested/shape.png').write_bytes(PNG)
        for path, expected, kind in (('/amc-bank/bank.js', bundle, 'javascript'),
                                     ('/amc-bank/figures/shape.png', PNG, 'image/png'),
                                     ('/amc-bank/figures/shape.svg', SVG, 'image/svg+xml')):
            with self.subTest(path=path):
                code, headers, data = self.request(path)
                self.assertEqual(code, 200)
                self.assertEqual(data, expected)
                self.assertIn(kind, headers['Content-Type'])
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        for path in ('/amc-bank/config.json', '/amc-bank/questions/' + record['ID'] + '.json',
                     '/amc-bank/figures/config.json', '/amc-bank/figures/nested/shape.png',
                     '/amc-bank/figures/../config.json', '/amc-bank/figures/%2e%2e/config.json',
                     '/amc-bank/figures/%2e%2e%2fconfig.json', '/amc-bank/figures/..%5cconfig.json',
                     '/amc-bank/figures/shape.png/extra', '/amc-bank/figures/missing.png',
                     '/math-practice/amc-bank.js', '/question%20bank/figures/shape.png'):
            with self.subTest(path=path):
                code, _, data = self.request(path)
                self.assertEqual(code, 404)
                self.assertNotIn(b'private', data)

    def test_only_the_eight_official_amc_solution_pdfs_are_public(self):
        bank, _ = self.make_amc_question()
        official = bank / 'official-solutions'
        official.mkdir()
        for filename in ('AMC8_2023_Solutions.pdf', 'AMC8_2022_Solutions.pdf',
                         'AMC8_2020_Solutions.pdf', 'AMC8_2019_Solutions.pdf',
                         'AMC8_2018_Solutions.pdf', 'AMC10A_2022_Solutions.pdf',
                         'AMC10A_2021_Spring_Solutions.pdf', 'AMC10A_2021_Fall_Solutions.pdf'):
            expected = b'%PDF-1.4\n' + filename.encode('ascii')
            (official / filename).write_bytes(expected)
            code, headers, data = self.request('/amc-bank/official-solutions/' + filename)
            self.assertEqual(code, 200)
            self.assertEqual(headers['Content-Type'], 'application/pdf')
            self.assertEqual(data, expected)
        (official / 'unrelated.pdf').write_bytes(b'%PDF-1.4\nprivate')
        (official / 'config.json').write_bytes(b'{"secret":"private"}')
        (bank / 'config.json').write_bytes(b'{"secret":"private"}')
        for path in ('/amc-bank/official-solutions/unrelated.pdf',
                     '/amc-bank/official-solutions/config.json',
                     '/amc-bank/official-solutions/../config.json',
                     '/amc-bank/official-solutions/%2e%2e/config.json',
                     '/amc-bank/official-solutions/%2e%2e%2fconfig.json',
                     '/amc-bank/official-solutions/..%5cconfig.json',
                     '/amc-bank/official-solutions/../official-solutions/AMC8_2023_Solutions.pdf',
                     '/amc-bank/official-solutions/AMC8_2023_Solutions.pdf/extra'):
            with self.subTest(path=path):
                code, _, data = self.request(path)
                self.assertEqual(code, 404)
                self.assertNotIn(b'private', data)


if __name__ == '__main__':
    unittest.main()
