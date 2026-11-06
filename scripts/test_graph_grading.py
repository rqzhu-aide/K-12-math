"""Current central adjudications affect grading without changing source questions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from knowledge_graph import build_database, context_for_question, question_fingerprint
from practice_tutor import review_submission
from question_answers import confirmed_grading_notice, effective_grading_question
from student_assessment import ModelConfig, StudentAssessment


ROOT = Path(__file__).resolve().parents[1]


class GraphGradingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='graph-grading-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.question = {'ID': 'cnm_001_q1', 'Bank': 'cn-math', 'Language': 'en',
                         'Question': 'What is 2+2?', 'Choices': {}, 'Correct Answer': '5',
                         'ResponseType': 'numeric', 'Solution': 'The bank incorrectly says five.'}

    def build(self, status, *, mapping_status='mapped'):
        self.path = self.root / 'cn-math-bank/questions' / (self.question['ID'] + '.json')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.question), encoding='utf-8')
        source = self.root / 'knowledge-graph/source'
        source.mkdir(parents=True, exist_ok=True)
        values = {'metadata': {'version': 'grading-test-v1'},
                  'nodes': [{'id': 'fixture:target', 'name': 'Fixture task', 'description': 'The displayed task.',
                             'kind': 'concept', 'reviewStatus': 'fixture_reviewed', 'criteria': [], 'aliases': []}],
                  'relationships': []}
        for field, value in values.items():
            (source / (field + '.json')).write_text(json.dumps(value), encoding='utf-8')
        mapping = {'questionId': self.question['ID'], 'bank': self.question['Bank'],
                   **question_fingerprint(self.question, root=self.root), 'status': mapping_status,
                   'reviewStatus': 'fixture_reviewed', 'assessedIds': ['fixture:target'],
                   'supportIds': [], 'routes': [], 'flags': ['confirmed_answer_key_conflict'],
                   'rationale': 'A content-bound fixture for central adjudication.',
                   'answerCheck': {'status': status, 'reason': 'Independent adjudication of the displayed task.'},
                   'reviews': [{'reviewer': 'fixture'}]}
        if mapping_status == 'non_diagnostic':
            mapping.update(assessedIds=[], contextualIds=['fixture:target'], flags=['answer_relation_supplied'])
        (source / 'mappings.jsonl').write_text(json.dumps(mapping) + '\n', encoding='utf-8')
        build_database(self.root)

    def attempt(self, answer='4'):
        return {'questionId': self.question['ID'], 'answer': answer, 'thoughts': 'Two pairs total four.',
                'category': 'partial', 'answerCategory': 'wrong'}

    def test_only_explicit_confirmed_statuses_produce_notices(self):
        for status in ('confirmed_conflict', 'confirmed_ambiguous'):
            self.assertEqual(confirmed_grading_notice({'status': status})['gradingStatus'], 'disputed')
        for value in (None, {}, {'status': 'ambiguous'}, {'status': 'disagrees'},
                      {'status': 'matches'}, {'status': 'confirmed'}, 'confirmed_conflict'):
            self.assertIsNone(confirmed_grading_notice(value))

    def test_current_confirmed_outcomes_do_not_grade_or_mutate_source(self):
        for status in ('confirmed_conflict', 'confirmed_ambiguous'):
            with self.subTest(status=status):
                self.build(status)
                before = self.path.read_bytes()
                original = deepcopy(self.question)
                view = effective_grading_question(self.question, root=self.root)
                self.assertEqual(view['GradingStatus'], 'disputed')
                self.assertEqual(self.question, original)
                self.assertNotIn('GradingStatus', self.question)
                result = StudentAssessment(ModelConfig(), root=self.root).assess(self.attempt())
                self.assertEqual(result['answerCategory'], 'not_graded')
                self.assertIsNone(result['answerCorrect'])
                self.assertFalse(result['modelUsed'])
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(context_for_question(self.question, root=self.root)['binding']['status'], 'current')

    def test_tutor_returns_not_graded_before_requesting_any_model(self):
        self.build('confirmed_conflict')
        assessor, settings, transport = MagicMock(), MagicMock(), MagicMock()
        assessor.root = self.root
        assessor.submission.return_value = (self.question, '4', 'Two pairs total four.')
        result = review_submission(assessor, settings, transport, self.attempt(), chatgpt=transport)
        self.assertEqual(result['answerCategory'], 'not_graded')
        self.assertEqual(result['gradingStatus'], 'disputed')
        settings.inference_configured.assert_not_called()
        transport.infer.assert_not_called()

    def test_first_pass_disagreement_and_flags_do_not_disable_grading(self):
        for status in ('disagrees', 'ambiguous', 'matches'):
            with self.subTest(status=status):
                self.build(status)
                self.assertIs(effective_grading_question(self.question, root=self.root), self.question)
                result = StudentAssessment(ModelConfig(), root=self.root).assess(self.attempt())
                self.assertEqual(result['answerCategory'], 'wrong')

    def test_confirmed_unresolved_mapping_still_carries_adjudication(self):
        self.build('confirmed_ambiguous', mapping_status='unresolved')
        result = StudentAssessment(ModelConfig(), root=self.root).assess(self.attempt())
        self.assertEqual(result['answerCategory'], 'not_graded')

    def test_non_diagnostic_context_keeps_ordinary_grading(self):
        self.question.update(Question='The result has the same count, 6. What is the resulting count?',
                             **{'Correct Answer': '6', 'Solution': 'The count is supplied.'})
        self.build('matches', mapping_status='non_diagnostic')
        before = self.path.read_bytes()
        self.assertIs(effective_grading_question(self.question, root=self.root), self.question)
        result = StudentAssessment(ModelConfig(), root=self.root).assess(self.attempt(answer='6'))
        self.assertEqual(result['answerCategory'], 'correct')
        self.assertTrue(result['answerCorrect'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_stale_content_or_pixels_cannot_authorize_a_dispute(self):
        self.build('confirmed_conflict')
        changed = {**self.question, 'Question': 'What is 3+2?'}
        self.assertIs(effective_grading_question(changed, root=self.root), changed)
        figures = self.root / 'cn-math-bank/figures'
        figures.mkdir()
        image = figures / 'shape.svg'
        image.write_text('<svg>original</svg>', encoding='utf-8')
        self.question['Question'] += ' [Figure 1](figures/shape.svg)'
        self.build('confirmed_conflict')
        image.write_text('<svg>changed</svg>', encoding='utf-8')
        self.assertIs(effective_grading_question(self.question, root=self.root), self.question)

    def test_stale_projection_cannot_override_a_content_current_central_dispute(self):
        from knowledge_graph import mapping_record
        from knowledge_graph_questions import graph_payload
        for mapping_status in ('mapped', 'unresolved'):
            with self.subTest(mapping_status=mapping_status):
                self.build('confirmed_conflict', mapping_status=mapping_status)
                central = mapping_record(self.question['ID'], self.root)
                self.question['KnowledgeGraph'] = graph_payload(central, 'earlier-graph-version')
                self.path.write_text(json.dumps(self.question), encoding='utf-8')
                before = self.path.read_bytes()
                context = context_for_question(self.question, self.root, max_chars=512)
                self.assertEqual(context['status'], 'stale')
                self.assertEqual(context['binding']['status'], 'current')
                self.assertEqual(context['answerCheck']['status'], 'confirmed_conflict')
                self.assertEqual(context['nodes'], [])
                self.assertEqual(context['routes'], [])
                result = StudentAssessment(ModelConfig(), root=self.root).assess(self.attempt())
                self.assertEqual(result['answerCategory'], 'not_graded')
                self.assertEqual(self.path.read_bytes(), before)
                changed = {**self.question, 'Question': 'What is 3+2?'}
                self.assertIs(effective_grading_question(changed, root=self.root), changed)

    def test_portable_stub_alone_has_no_backend_grading_authority(self):
        self.question['KnowledgeGraph'] = {'version': 'forged', 'contentHash': '0' * 64,
                                           'gradingStatus': 'disputed', 'gradingNote': 'A supplied claim.'}
        self.assertIs(effective_grading_question(self.question, root=self.root), self.question)

    def test_actual_ambiguous_english_item_keeps_original_key_and_provenance(self):
        self.question = json.loads((ROOT / 'cn-math-bank/questions/cnm_074_q3.json').read_text(encoding='utf-8'))
        self.question.pop('KnowledgeGraph', None)
        self.build('confirmed_ambiguous')
        before = self.path.read_bytes()
        result = StudentAssessment(ModelConfig(), root=self.root).assess(self.attempt(answer='A'))
        self.assertEqual(result['answerCategory'], 'not_graded')
        self.assertEqual(self.question['Correct Answer'], 'D')
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
