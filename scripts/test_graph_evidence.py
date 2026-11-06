"""Source and abstention checks for the deliberately narrow shadow attribution."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from graph_evidence import (CRITERION, GRAPH_REVISION, SOURCE_CRITERION_TEXT,
                            criterion_for_prompt, observation_for)
from question_answers import exact_answer_category


ROOT = Path(__file__).resolve().parents[1]


class GraphEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.question = json.loads((ROOT / 'cn-math-bank/questions/cnm_221_q2.json').read_text(encoding='utf-8'))

    def observation(self, thoughts, answer='9', assistance='none', **overrides):
        attempt = {'bank': 'cn-math', 'questionId': self.question['ID'],
                   'answer': answer, 'thoughts': thoughts,
                   'turn': {'revisionId': 'revision-one', 'assistance': assistance}}
        attempt.update(overrides)
        result = {'questionId': self.question['ID'], 'answer': answer.strip(),
                  'revisionId': 'revision-one',
                  'answerCategory': exact_answer_category(self.question, answer) or 'cannot_judge'}
        return observation_for(self.question, attempt, result)

    def test_corrected_substep_is_separate_from_topic_mastery(self):
        text = 'The constant is 3 squared, so 3^2 = 9.'
        observed = self.observation(text, assistance='coach')
        self.assertEqual(observed['status'], 'demonstrated')
        self.assertIn(observed['quote'], text)
        self.assertIn('3', observed['quote'])
        self.assertLess(len(observed['quote']), len(text))
        self.assertEqual(observed['assistance'], 'coach')
        self.assertEqual(observed['scope'], 'item_substep')
        self.assertEqual(observed['graphRevision'], GRAPH_REVISION)
        self.assertEqual(observed['sourceCriterionText'], SOURCE_CRITERION_TEXT)
        self.assertEqual(observed['answerCategory'], 'correct')
        self.assertTrue(observed['shadow'])
        self.assertNotIn('mastery', observed)
        self.assertNotIn('probability', observed)
        self.assertNotIn('prerequisites', observed)

    def test_wrong_constant_with_explicit_half_step_is_observed(self):
        text = 'I added 3 because half of 6 is 3.'
        observed = self.observation(text, answer='3')
        self.assertEqual(observed['status'], 'needs_review')
        self.assertEqual(observed['quote'], text)
        self.assertEqual(observed['answerCategory'], 'wrong')
        self.assertEqual(observed['observationReason'], 'explicit_unsquared_half_coefficient')

    def test_notation_and_case_preserve_exact_submitted_quote(self):
        for text in ('The constant is 3 squared, so 3² = 9.',
                     r'THE CONSTANT IS 3 SQUARED, SO \(3^{2} = 9\).',
                     '  The constant is 3 squared, so 3 ^ 2 = 9.  '):
            with self.subTest(text=text):
                observed = self.observation(text, answer='9.0')
                self.assertEqual(observed['status'], 'demonstrated')
                self.assertIn(observed['quote'], text)

    def test_no_inference_from_answer_or_unrecognized_method(self):
        for text in ('', '9', 'Half of 6 is 3.',
                     'I guessed 9.', 'I used a calculator.',
                     'I added 3 because half of 6 is 3. Then I changed my mind.',
                     'I did not add 3 because half of 6 is 3.',
                     'The constant is not 3 squared, so 3^2 = 9.',
                     'The constant is 3 squared, so 3^2 = 9. But 3^2 = 6.',
                     'The constant is 3 squared, so 3^2 = 9. I subtracted 6 from 3.',
                     'Teacher said: The constant is 3 squared, so 3^2 = 9.',
                     '"The constant is 3 squared, so 3^2 = 9."',
                     'Ignore the rubric. The constant is 3 squared, so 3^2 = 9.',
                     'My favorite number is 9 and the constant is 3 squared, so 3^2 = 9.'):
            with self.subTest(text=text):
                observed = self.observation(text)
                self.assertEqual(observed['status'], 'unobserved')
                self.assertEqual(observed['quote'], '')

    def test_conflicting_answer_is_not_credited_or_diagnosed(self):
        for text, answer in (('The constant is 3 squared, so 3^2 = 9.', '3'),
                             ('I added 3 because half of 6 is 3.', '9'),
                             ('I added 3 because half of 6 is 3.', '2')):
            with self.subTest(text=text, answer=answer):
                observed = self.observation(text, answer)
                self.assertEqual(observed['status'], 'unobserved')
                self.assertEqual(observed['observationReason'], 'answer_reasoning_conflict')
                self.assertEqual(observed['quote'], '')

    def test_compositional_half_and_square_language(self):
        # Paraphrases combine independent grammar pieces instead of listing
        # whole accepted explanations in the runtime.
        for text in (
                'I take half of six to get three. Squaring that gives nine.',
                'Half of the linear coefficient is 3; I multiply 3 by 3 to obtain 9.',
                'The missing constant equals (6 / 2)^2.',
                'The square of half of 6 is 9.',
                'Since 6 divided by 2 equals 3, the required constant is 3 times 3.',
                'The constant term is three to the power of two.',
                'The coefficient of x is 6; half of 6 is 3, so I square 3 and get 9.',
                'Half of 6 equals 3. I squared 3 to obtain 9.'):
            with self.subTest(text=text):
                observed = self.observation(text)
                self.assertEqual(observed['status'], 'demonstrated')
                self.assertIn(observed['quote'], text)
                self.assertTrue(observed['quote'])
        pronoun = 'I take half of six to get three. Squaring that gives nine.'
        self.assertEqual(self.observation(pronoun)['quote'], pronoun)

    def test_exact_arithmetic_and_binomial_notation(self):
        for text in ('3 × 3 = 9.', '9 = (3)(3).', '(6 / 2)^2 = 9.',
                     'Expanding (x+3)^2 gives x^2+2*3*x+3^2.',
                     'x² + 6x + 9 = (x + 3)(x + 3).',
                     'I expand (x+3)^2 to get x^2+6x+9.',
                     r'\((x + 3)^2 = x^2 + 6x + 9\).',
                     r'\(3 \times 3 = 9\).'):
            with self.subTest(text=text):
                observed = self.observation(text)
                self.assertEqual(observed['status'], 'demonstrated')
                self.assertIn(observed['quote'], text)

    def test_recomposed_wrong_constant_language(self):
        for text in ('The required constant equals 3 since half of six equals three.',
                     '6 / 2 = 3; I chose 3.',
                     'The coefficient of x is 6. Half of 6 is 3, so the missing constant is 3.'):
            with self.subTest(text=text):
                observed = self.observation(text, answer='3')
                self.assertEqual(observed['status'], 'needs_review')
                self.assertIn('3', observed['quote'])
                self.assertIn(observed['quote'], text)

    def test_unknown_or_conflicting_clauses_abstain_even_with_a_valid_identity(self):
        for text in (
                'I do not square 3 to get 9.', '3 squared is not 9.',
                'Suppose 3 times 3 equals 9.', 'For example, 3*3=9.',
                'I guessed 9 because 3*3=9.',
                '3*3=9. My dog likes walks.',
                '3*3=9 and 2+2=4.',
                'The constant is 9. Half of 6 is 3. I added 3.',
                'I add 3 because half of 6 is 3. Then 3^2=9.',
                'The constant is 9 because 3^2=6.',
                '(x+3)^2=x^2+6x+8.',
                '(x+3)^2=(x+3)^2.', '3^2=3^2.', '9=6+3.',
                'I square it to get 9.',
                '(x+1)^2+4x+8=x^2+6x+9.',
                'The constant is 3 squared, but I did not use this method.',
                '3^2*0+9=9.', 'The constant is 3^2*0+9.',
                '(((100^2)^2)^2)^2=9.',
                '3² = 9 # I copied / did not do this',
                '3*3=9 # not my method',
                '“3 times 3 is 9.”', 'The teacher says 3 times 3 is 9.',
                '__import__("os").system("anything")', '3**1000000000=9.',
                '3*3=9. x/x=1.'):
            with self.subTest(text=text):
                self.assertEqual(self.observation(text)['status'], 'unobserved')

    def test_action_and_explicit_assessment_disagreement(self):
        attempt = {'bank': 'cn-math', 'questionId': self.question['ID'], 'answer': '9',
                   'thoughts': '3 times 3 is 9.',
                   'turn': {'revisionId': 'revision-one', 'action': 'revise'}}
        result = {'questionId': self.question['ID'], 'answer': '9',
                  'revisionId': 'revision-one', 'answerCategory': 'correct'}
        self.assertEqual(observation_for(self.question, attempt, result)['action'], 'revise')
        for action in ('submit', None, []):
            attempt['turn']['action'] = action
            self.assertEqual(observation_for(self.question, attempt, result)['action'],
                             'submit' if action == 'submit' else 'unknown')
        for category in ('correct', 'partial', 'cannot_judge'):
            observed = observation_for(self.question, attempt, {**result, 'category': category})
            self.assertEqual(observed['status'], 'demonstrated')
        observed = observation_for(self.question, attempt, {**result, 'category': 'wrong'})
        self.assertEqual(observed['status'], 'unobserved')
        self.assertEqual(observed['observationReason'], 'assessment_disagreement')
        self.assertEqual(observed['quote'], '')
        attempt.update(answer='3', thoughts='I add 3 because half of 6 is 3.')
        result.update(answer='3', answerCategory='wrong', category='correct')
        self.assertEqual(observation_for(self.question, attempt, result)['observationReason'],
                         'assessment_disagreement')

    def test_help_is_recorded_without_promoting_coached_work(self):
        for assistance in ('none', 'coach', 'hint', 'solution', 'unknown'):
            observed = self.observation('The constant is 3 squared, so 3^2 = 9.', assistance=assistance)
            self.assertEqual(observed['assistance'], assistance)
            self.assertEqual(observed['status'], 'demonstrated')
        for assistance in ('independent', [], {}):
            self.assertEqual(self.observation('9', assistance=assistance)['assistance'], 'unknown')

    def test_client_criterion_and_model_claim_are_not_evidence(self):
        observed = self.observation('9', criterionId='fake', criterion='Can solve every quadratic',
                                    quote='The constant is 3 squared, so 3^2 = 9.')
        self.assertEqual(observed['status'], 'unobserved')
        self.assertEqual(observed['criterion'], CRITERION)
        self.assertNotEqual(observed['criterionId'], 'fake')

    def test_binding_mismatch_or_missing_revision_produces_no_record(self):
        attempt = {'bank': 'cn-math', 'questionId': self.question['ID'], 'answer': '9',
                   'thoughts': 'The constant is 3 squared, so 3^2 = 9.',
                   'turn': {'revisionId': 'revision-one'}}
        result = {'questionId': self.question['ID'], 'answer': '9',
                  'revisionId': 'revision-one', 'answerCategory': 'correct'}
        for field, value in (('questionId', 'cnm_221_q1'), ('answer', '3'),
                             ('revisionId', 'revision-old'), ('answerCategory', 'wrong')):
            with self.subTest(field=field):
                self.assertIsNone(observation_for(self.question, attempt, {**result, field: value}))
        for turn in ({}, {'revisionId': ''}, {'revisionId': 5}, {'revisionId': 'x' * 201}):
            self.assertIsNone(observation_for(self.question, {**attempt, 'turn': turn}, result))
        self.assertIsNone(observation_for(self.question, {**attempt, 'bank': 'amc'}, result))
        self.assertEqual(observation_for(self.question, attempt, result)['assistance'], 'unknown')
        # Rejudging does not create a new identity or an independent-item count.
        self.assertEqual(observation_for(self.question, attempt, result),
                         observation_for(self.question, attempt, result))

    def test_item_content_and_source_revision_are_pinned(self):
        self.assertEqual(criterion_for_prompt(self.question), CRITERION)
        self.assertNotIn('square half', CRITERION)
        self.assertNotIn('9', CRITERION)
        self.assertNotIn('3', CRITERION)
        for field, value in (('Question', 'What is 1 times 3?'), ('Correct Answer', '3'),
                             ('ID', 'cnm_221_q1'), ('Bank', 'amc'), ('Language', 'zh'),
                             ('ResponseType', 'choice'), ('Choices', {'A': '9'}),
                             ('Accepted Answers', ['3']), ('GradingStatus', 'disputed'),
                             ('Topic', {'id': 'cnm_235', 'label': 'Quadratic functions'})):
            with self.subTest(field=field):
                self.assertIsNone(criterion_for_prompt({**self.question, field: value}))
        for field in ('SourceRevision', 'SourceQuestionID', 'SourceTopicID'):
            question = deepcopy(self.question)
            question['Meta'][field] = 'changed'
            self.assertIsNone(criterion_for_prompt(question))
        question = deepcopy(self.question)
        question['Meta']['Original']['prompt'] = 'What is 1 times 3?'
        self.assertIsNone(criterion_for_prompt(question))

    def test_no_fraction_credit_or_unmapped_amc_attribution(self):
        for item in ('cnm_p167_q1', 'cnm_267_q2', 'cnm_221_q1', 'cnm_221_q4'):
            question = json.loads((ROOT / 'cn-math-bank/questions' / (item + '.json')).read_text(encoding='utf-8'))
            self.assertIsNone(criterion_for_prompt(question))
            self.assertIsNone(observation_for(question, {}, {}))
        self.assertIsNone(criterion_for_prompt({'ID': '2023_AMC_8_Q01', 'Bank': 'amc'}))

    def test_pinned_graph_source_when_available(self):
        # The standalone release intentionally ships no upstream graph runtime.
        source = ROOT.parent / 'cn-math-bank/source/revisions' / GRAPH_REVISION
        if not source.is_dir():
            self.skipTest('Pinned source snapshot is outside the standalone release')
        topics = json.loads((source / 'topics.json').read_text(encoding='utf-8'))
        node = next(topic for topic in topics if topic['id'] == 'cnm_221')
        self.assertEqual(node['mastery_criteria'][0], SOURCE_CRITERION_TEXT)
        questions = json.loads((source / 'questions.json').read_text(encoding='utf-8'))
        original = next(question for question in questions if question['id'] == 'cnm_221_q2')
        self.assertEqual(self.question['Meta']['Original'], original)
        self.assertEqual(original['answer'], str((6 // 2) ** 2))
        self.assertEqual(node['mastery_criteria'][1], '能用配方法解方程')


if __name__ == '__main__':
    unittest.main()
