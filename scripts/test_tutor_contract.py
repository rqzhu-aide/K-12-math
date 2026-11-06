"""Reference availability and blank-thinking behavior in the single tutor review."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from practice_tutor import SCHEMA, review_prompt, review_submission, validate_review
from question_banks import reference_solution
from student_assessment import AssessmentError, ModelConfig, StudentAssessment


QUESTION = {'ID': 'cnm_999_q1', 'Bank': 'cn-math', 'Language': 'en', 'ResponseType': 'numeric',
            'Question': 'What is 2 + 2?', 'Choices': {}, 'Correct Answer': '4',
            'Solution': 'Add the two groups: \\(2+2=4\\).',
            'Meta': {'SolutionSource': 'Synthetic source, not independently reviewed',
                     'SolutionStatus': 'Unreviewed', 'SourceRevision': 'fixture-one',
                     'Original': {'private': 'Excluded source record'}}}
ACCOUNT = {'provider': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'xhigh'}
OMITTED_STATUS = 'Third-party worked solution not included in this distribution'


class ReferenceAvailabilityTests(unittest.TestCase):
    def prompt(self, question):
        with patch('practice_tutor.context_for', return_value={'contextSource': 'displayed_task'}):
            return json.loads(review_prompt(question, '4', 'I added both groups.',
                                           'cannot_judge', 'correct', 'correct'))

    def test_present_reference_is_complete_and_keeps_its_review_provenance(self):
        before = deepcopy(QUESTION)
        reference = self.prompt(QUESTION)['reference']
        self.assertEqual(reference['solutionAvailability'], 'present')
        self.assertEqual(reference['solution'], QUESTION['Solution'])
        self.assertEqual(reference['solutionOmittedReason'], '')
        self.assertEqual(reference['solutionProvenance']['source'], QUESTION['Meta']['SolutionSource'])
        self.assertEqual(reference['solutionProvenance']['reviewStatus'], 'Unreviewed')
        self.assertNotIn('Excluded source record', json.dumps(reference))
        self.assertEqual(QUESTION, before)

    def test_missing_reference_is_explicit_without_fabricating_a_solution(self):
        for value in ('', '   ', None):
            with self.subTest(solution=value):
                question = {**QUESTION, 'Solution': value}
                reference = self.prompt(question)['reference']
                self.assertEqual(reference['solutionAvailability'], 'missing')
                self.assertEqual(reference['solution'], '')
                self.assertEqual(reference['answer'], '4')
                self.assertEqual(reference['solutionOmittedReason'], '')
                self.assertEqual(question['Solution'], value)
        without_field = {key: value for key, value in QUESTION.items() if key != 'Solution'}
        self.assertEqual(self.prompt(without_field)['reference']['solutionAvailability'], 'missing')

    def test_distribution_omission_is_distinct_from_missing_and_keeps_the_reason(self):
        question = {**QUESTION, 'Solution': '', 'Meta': {'SolutionStatus': OMITTED_STATUS}}
        reference = self.prompt(question)['reference']
        self.assertEqual(reference['solutionAvailability'], 'deliberately_omitted')
        self.assertEqual(reference['solution'], '')
        self.assertEqual(reference['solutionOmittedReason'], OMITTED_STATUS)
        self.assertEqual(reference['solutionProvenance']['reviewStatus'], OMITTED_STATUS)

    def test_reviewed_mismatch_is_omitted_but_repaired_text_can_be_used(self):
        question = {**QUESTION, 'ID': 'cnm_p167_q1', 'Question': 'Calculate: \\(1\\times3=?\\)',
                    'Correct Answer': '3',
                    'Solution': 'Multiply both the numerator and denominator of \\(\\frac{1}{2}\\) by 3. The new numerator is 3.'}
        omitted = reference_solution(question)
        self.assertEqual(omitted['availability'], 'deliberately_omitted')
        self.assertEqual(omitted['text'], '')
        self.assertIn('Reviewed mismatch', omitted['omittedReason'])
        repaired = reference_solution({**question, 'Solution': 'Multiplying 1 by 3 gives 3.'})
        self.assertEqual(repaired['availability'], 'present')
        self.assertEqual(repaired['text'], 'Multiplying 1 by 3 gives 3.')


class BlankThinkingReviewTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        temporary = tempfile.TemporaryDirectory(prefix='tutor-contract-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        folder = self.root / 'cn-math-bank/questions'
        folder.mkdir(parents=True)
        self.path = folder / (QUESTION['ID'] + '.json')
        self.path.write_text(json.dumps(QUESTION), encoding='utf-8')
        self.assessor = StudentAssessment(ModelConfig(), root=self.root)
        self.settings, self.account = MagicMock(), MagicMock()
        self.settings.inference_configured.return_value = True
        self.settings.inference_config.return_value = ACCOUNT

    def review(self, answer, thoughts, model, **initial):
        self.account.infer.return_value = json.dumps(model)
        attempt = {'questionId': QUESTION['ID'], 'answer': answer, 'thoughts': thoughts,
                   'category': 'cannot_judge', 'answerCategory': 'cannot_judge', **initial}
        with patch('practice_tutor.request', side_effect=AssertionError('Use only the selected account')):
            return review_submission(self.assessor, self.settings, self.account, attempt)

    def test_blank_thinking_cannot_be_judged_correct_or_wrong_from_the_answer(self):
        for answer, raw_category, expected_answer in (('4', 'correct', 'correct'), ('5', 'wrong', 'wrong')):
            with self.subTest(answer=answer):
                self.account.reset_mock()
                result = self.review(answer, '   ', {
                    'category': raw_category, 'answerCategory': expected_answer,
                    'coach': 'Your explanation is correct.' if raw_category == 'correct' else 'You distributed incorrectly.',
                    'hint': 'Repeat that reasoning.'})
                self.assertEqual(result['category'], 'partial')
                self.assertEqual(result['answerCategory'], expected_answer)
                self.assertEqual(result['modelJudgment']['category'], raw_category)
                self.assertIn('first step', result['coach'])
                self.assertNotIn('distributed', result['coach'])
                self.assertEqual(result['hint'], '')
                self.assertEqual(result['clarification'], result['coach'])
                self.account.infer.assert_called_once()
                prompt = json.loads(self.account.infer.call_args.args[1])
                self.assertEqual(prompt['studentSubmission'], {'answer': answer, 'reasoning': ''})

    def test_consistent_partial_coach_is_retained_without_a_duplicate_hint(self):
        coach = 'Which operation would combine the two equal groups?'
        result = self.review('4', '', {'category': 'partial', 'answerCategory': 'correct',
                                       'coach': coach, 'hint': 'Which operation combines the groups?'})
        self.assertEqual(result['category'], 'partial')
        self.assertEqual(result['coach'], coach)
        self.assertEqual(result['hint'], '')
        self.account.infer.assert_called_once()

    def test_blank_work_is_reviewed_even_when_initial_labels_claim_both_correct(self):
        result = self.review('4', '', {'category': 'correct', 'answerCategory': 'correct',
                                      'coach': 'Your explanation is correct.', 'hint': ''},
                             category='correct', answerCategory='correct')
        self.assertEqual(result['category'], 'partial')
        self.account.infer.assert_called_once()

    def test_missing_reference_uses_one_review_and_preserves_the_four_output_fields(self):
        self.path.write_text(json.dumps({**QUESTION, 'Solution': ''}), encoding='utf-8')
        result = self.review('4', 'I counted two pairs.', {
            'category': 'correct', 'answerCategory': 'correct',
            'coach': 'You correctly combined both pairs.', 'hint': ''})
        self.assertEqual(result['category'], 'correct')
        self.account.infer.assert_called_once()
        call = self.account.infer.call_args
        self.assertEqual(call.args[0], ACCOUNT)
        prompt = json.loads(call.args[1])
        self.assertEqual(prompt['reference']['solutionAvailability'], 'missing')
        self.assertEqual(prompt['reference']['solution'], '')
        self.assertEqual(set(call.args[3]['properties']), {'category', 'answerCategory', 'coach', 'hint'})
        self.assertEqual(call.args[3], SCHEMA)
        self.assertFalse(SCHEMA['additionalProperties'])
        self.assertEqual(call.args[4], [])

    def test_nonblank_review_is_not_reclassified_and_complete_work_still_closes(self):
        result = self.review('4', 'I added two groups of two to get four.', {
            'category': 'correct', 'answerCategory': 'correct',
            'coach': 'You correctly combined both groups.', 'hint': ''})
        self.assertEqual(result['category'], 'correct')
        self.assertEqual(result['hint'], '')
        self.account.reset_mock()
        with self.assertRaises(AssessmentError):
            self.review('4', 'I added both groups.', {
                'category': 'correct', 'answerCategory': 'correct', 'coach': 'Correct.', 'hint': ''},
                category='correct', answerCategory='correct')
        self.account.infer.assert_not_called()

    def test_blank_thinking_keeps_partial_answer_credit_and_localized_first_step(self):
        result = validate_review(json.dumps({'category': 'wrong', 'answerCategory': 'correct',
                                             'coach': 'An invented sign error.', 'hint': ''}),
                                 known_category='partial', reasoning_provided=False, language='zh-CN')
        self.assertEqual(result['category'], 'partial')
        self.assertEqual(result['answerCategory'], 'partial')
        self.assertIsNone(result['answerCorrect'])
        self.assertIn('先做哪一步', result['coach'])
        self.assertEqual(result['hint'], '')


if __name__ == '__main__':
    unittest.main()
