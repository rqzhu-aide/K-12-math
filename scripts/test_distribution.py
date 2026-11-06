"""Verify the shipped question snapshot and its public distribution boundary."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

from question_banks import AMC_QUESTION_ID
from export_amc_bank import browser_question

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / 'cn-math-bank'
ADAPTED_EXAMS = {
    '2018_AMC_8': 'AMC8_2018_Solutions.pdf',
    '2019_AMC_8': 'AMC8_2019_Solutions.pdf',
    '2020_AMC_8': 'AMC8_2020_Solutions.pdf',
    '2022_AMC_8': 'AMC8_2022_Solutions.pdf',
    '2023_AMC_8': 'AMC8_2023_Solutions.pdf',
    '2021_AMC_10A': 'AMC10A_2021_Spring_Solutions.pdf',
    '2021_Fall_AMC_10A': 'AMC10A_2021_Fall_Solutions.pdf',
    '2022_AMC_10A': 'AMC10A_2022_Solutions.pdf',
}
OFFICIAL_ADAPTED_IDS = {f'{exam}_Q{n:02d}' for exam in ADAPTED_EXAMS for n in range(1, 26)}


class DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (BANK / 'bank.js').read_text(encoding='utf-8')
        cls.browser = json.loads(source.split('window.CN_MATH_BANK = ', 1)[1].rstrip().removesuffix(';'))
        cls.records = {p.stem: json.loads(p.read_text(encoding='utf-8'))
                       for p in (BANK / 'questions').glob('*.json')}

    def test_browser_and_backend_use_same_questions_and_answers(self):
        self.assertEqual(len(self.records), 3355)
        self.assertEqual(len(self.browser['questions']), 3355)
        self.assertEqual({q['id'] for q in self.browser['questions']}, set(self.records))
        fields = {'question': 'Question', 'choices': 'Choices', 'answer': 'Correct Answer',
                  'solution': 'Solution', 'responseType': 'ResponseType'}
        for question in self.browser['questions']:
            record = self.records[question['id']]
            self.assertEqual(record['Bank'], 'cn-math')
            for display, stored in fields.items():
                self.assertEqual(question[display], record[stored], question['id'] + ': ' + display)

    def test_originals_and_attribution_are_preserved(self):
        for record in self.records.values():
            meta = record['Meta']
            self.assertTrue(meta['Original'])
            self.assertEqual(meta['License'], 'CC-BY-NC-4.0')
            for key in ('SourceURL', 'SourceRevision', 'Attribution', 'Modifications'):
                self.assertTrue(meta[key], record['ID'] + ': ' + key)
        self.assertTrue((BANK / 'LICENSE').is_file())
        self.assertTrue((BANK / 'NOTICE.md').is_file())

    def test_display_diagrams_exist(self):
        used = set()
        for question in self.browser['questions']:
            for text in [question['question'], question['solution'], *question['choices'].values()]:
                for relative in re.findall(r'\[Figure \d+\]\(([^)]+)\)', text):
                    target = (BANK / relative).resolve()
                    self.assertTrue(target.is_relative_to(BANK), relative)
                    self.assertTrue(target.is_file(), relative)
                    used.add(relative)
        self.assertEqual(len(used), 156)
        self.assertEqual(len(list((BANK / 'figures').glob('*_zh.svg'))), 156)

    @unittest.skipUnless((ROOT / '.git').exists(), 'Git metadata is absent from exported archives')
    def test_local_files_and_legacy_sources_cannot_be_added_normally(self):
        private_paths = [
            'math-practice/config.json', 'math-practice/config.tmp', '.local/server.log',
            '.env', 'math-practice/.env.local', 'scripts/__pycache__/cache.pyc',
            'math-practice/amc-bank.js', 'question bank/questions/example.json',
            'cn-math-bank/source/raw.json', 'cn-math-bank/reports/check.json',
            'math-practice/test/screenshots/example.png', 'unrelated-personal-file.txt',
            'custom-banks/banks.js', 'custom-banks/private/questions/private__one.json',
            'knowledge-graph/local/mappings.jsonl', 'knowledge-graph/knowledge.sqlite3',
            'knowledge-graph/knowledge.sqlite3-wal', 'knowledge-graph/scratch.json',
            'knowledge-graph/source/unreviewed.json',
            'local-service/setting.yaml', 'local-service/api_key.txt',
            'scripts/local-service/SERVICES-GUIDE.md',
            'math-practice/setting.yaml', 'math-practice/settings.yml',
            'math-practice/auth.json', 'math-practice/secret.key',
            'question-bank-template/private-notes.txt',
        ]
        result = subprocess.run(['git', 'check-ignore', '-z', '--stdin'], cwd=ROOT,
                                input=('\0'.join(private_paths) + '\0').encode(),
                                capture_output=True, check=True)
        self.assertEqual(set(result.stdout.decode().rstrip('\0').split('\0')), set(private_paths))


class AmcDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = ROOT / 'amc-bank'
        source = (cls.bank / 'bank.js').read_text(encoding='utf-8')
        cls.browser = json.loads(source.split('window.AMC_BANK = ', 1)[1].rstrip().removesuffix(';'))
        cls.records = {p.stem: json.loads(p.read_text(encoding='utf-8'))
                       for p in (cls.bank / 'questions').glob('*.json')}

    def test_browser_and_backend_use_all_amc_questions_and_answers(self):
        self.assertEqual(len(self.records), 5435)
        self.assertEqual(len(self.browser['questions']), 5435)
        self.assertEqual(self.browser['id'], 'amc')
        self.assertEqual(self.browser['figuresBase'], '../amc-bank/figures/')
        self.assertEqual(self.browser['license'], 'CC-BY-NC-SA-4.0')
        self.assertEqual({q['id'] for q in self.browser['questions']}, set(self.records))
        fields = {'year': 'Year', 'level': 'Level', 'batch': 'Batch', 'number': 'Number',
                  'question': 'Question', 'questionType': 'Question Type',
                  'choices': 'Choices', 'choicesType': 'Choices Type',
                  'answer': 'Correct Answer', 'solution': 'Solution'}
        for question in self.browser['questions']:
            record = self.records[question['id']]
            self.assertEqual(record['Bank'], 'amc')
            self.assertIsNotNone(AMC_QUESTION_ID.fullmatch(record['ID']))
            self.assertEqual(record['ID'], question['id'])
            self.assertIn(record['Correct Answer'], record['Choices'])
            self.assertEqual(bool(record['Solution']), question['id'] in OFFICIAL_ADAPTED_IDS,
                             question['id'] + ': only the reviewed 200-question batch has worked solutions')
            for display, stored in fields.items():
                self.assertEqual(question[display], record[stored], question['id'] + ': ' + display)
        self.assertIn('1950_AMC_12_Q50', self.records)
        self.assertIn('2021_Fall_AMC_10A_Q01', self.records)

    def test_display_figures_match_the_shipped_amc_assets(self):
        used = set()
        for question in self.browser['questions']:
            for text in [question['question'], question['solution'], *question['choices'].values()]:
                for relative in re.findall(r'\[Figure \d+\]\(([^)]+)\)', text):
                    target = (self.bank / relative).resolve()
                    self.assertTrue(target.is_relative_to(self.bank / 'figures'), relative)
                    self.assertTrue(target.is_file(), relative)
                    used.add(relative)
        self.assertTrue(used)
        self.assertEqual(used, {'figures/' + p.name for p in (self.bank / 'figures').iterdir() if p.is_file()})

    def test_amc_attribution_and_withheld_solution_sources_are_preserved(self):
        for record in self.records.values():
            meta = record['Meta']
            self.assertEqual(meta['License'], 'CC-BY-NC-SA-4.0', record['ID'])
            self.assertIn('American Mathematics Competitions', meta['Attribution'], record['ID'])
            self.assertIn('Mathematical Association of America (MAA)', meta['Attribution'], record['ID'])
            for note in (meta.get('EditorialNote', ''), record.get('Source Content Note', '')):
                self.assertNotIn('processing code/', note, record['ID'])
            if record['ID'] in OFFICIAL_ADAPTED_IDS:
                self.assertEqual(meta['SolutionSource'], 'Adapted from MAA official solutions')
                self.assertEqual(meta['SolutionSourceURL'], meta['OfficialSolution']['sourceURL'])
                self.assertEqual(meta['SolutionAdaptation']['reviewStatus'], 'reviewed')
                self.assertEqual(meta['SolutionAdaptation']['officialPage'], meta['OfficialSolution']['page'])
            else:
                self.assertEqual(meta['SolutionSource'], '', record['ID'])
        for question in self.browser['questions']:
            meta = self.records[question['id']]['Meta']
            self.assertEqual(question['solutionSource'], meta['SolutionSource'])
            self.assertEqual(question['solutionSourceURL'], meta.get('SolutionSourceURL', ''))
        self.assertTrue((self.bank / 'LICENSE').is_file())
        self.assertTrue((self.bank / 'NOTICE.md').is_file())

    def test_export_rejects_copied_or_unreviewed_solutions(self):
        record = json.loads(json.dumps(self.records['2023_AMC_8_Q01']))
        record['Meta']['SolutionSource'] = 'live-poshenloh'
        with self.assertRaises(ValueError):
            browser_question(record)
        record['Meta']['SolutionSource'] = 'Adapted from MAA official solutions'
        record['Meta']['SolutionAdaptation']['reviewStatus'] = 'pending'
        with self.assertRaises(ValueError):
            browser_question(record)

    def test_official_solution_booklets_cover_exactly_their_200_questions(self):
        expected = {exam: 'official-solutions/' + name for exam, name in ADAPTED_EXAMS.items()}
        expected_ids = {f'{exam}_Q{number:02d}' for exam in expected for number in range(1, 26)}
        backend_refs = {key: record['Meta']['OfficialSolution'] for key, record in self.records.items()
                        if 'OfficialSolution' in record['Meta']}
        browser_refs = {question['id']: question['officialSolution'] for question in self.browser['questions']
                        if 'officialSolution' in question}
        self.assertEqual(set(backend_refs), expected_ids)
        self.assertEqual(browser_refs, backend_refs)
        manifest = json.loads((self.bank / 'sources.json').read_text(encoding='utf-8'))['officialSolutions']
        self.assertEqual(len(expected_ids), 200)
        self.assertEqual(len(manifest), 8)
        self.assertEqual({source['exam'] for source in manifest}, set(expected))
        self.assertEqual({path.name for path in (self.bank / 'official-solutions').iterdir()},
                         {Path(filename).name for filename in expected.values()})
        for source in manifest:
            filename = expected[source['exam']]
            source_url = source['url']
            self.assertEqual(source['file'], filename)
            self.assertEqual(source['url'], source_url)
            self.assertFalse(source['modified'])
            self.assertEqual(source['license'], 'CC-BY-NC-SA-4.0')
            path = (self.bank / source['file']).resolve()
            self.assertTrue(path.is_relative_to(self.bank / 'official-solutions'))
            data = path.read_bytes()
            self.assertTrue(data.startswith(b'%PDF-'), filename)
            self.assertEqual(hashlib.sha256(data).hexdigest(), source['sha256'], filename)
            for number in range(1, 26):
                reference = backend_refs[f'{source["exam"]}_Q{number:02d}']
                self.assertEqual(reference['url'], '../amc-bank/' + filename)
                self.assertEqual(reference['sourceURL'], source_url)
                self.assertEqual(reference['license'], source['license'])
                self.assertEqual(reference['attribution'], source['attribution'])
                self.assertIsInstance(reference['page'], int)
                self.assertGreaterEqual(reference['page'], 1)
                self.assertLessEqual(reference['page'], source.get('pages', 23))


if __name__ == '__main__':
    unittest.main()
