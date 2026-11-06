"""Connection tests must exercise the same structured text review as the tutor."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from model_connections import test_inference as check_api
from openai_connection import OpenAIConnection
from practice_tutor import (INSTRUCTIONS, SCHEMA, normalize_turn, reference_solution,
                            review_prompt, review_submission, validate_review,
                            test_tutor_connection as check_tutor)
from student_assessment import AssessmentError, ModelConfig, StudentAssessment
from knowledge_graph import build_database, question_fingerprint


QUESTION = {'Question': 'What is 2 + 2?', 'Choices': {}, 'Correct Answer': '4',
            'Solution': 'Add two and two to get four.', 'ResponseType': 'numeric'}
ATTEMPT = {'questionId': 'test__addition', 'answer': '4', 'thoughts': 'I added two and two.',
           'category': 'cannot_judge', 'answerCategory': 'correct'}
REVIEW = {'category': 'correct', 'answerCategory': 'correct', 'coach': 'Your explanation is correct.', 'hint': ''}
API = {'provider': 'api', 'model': 'test-model', 'bases': ['https://provider.example/v1'], 'apiKey': 'test-key'}
ACCOUNT = {'model': 'test-account-model', 'effort': 'xhigh'}
LEGACY_MULTIPLICATION = {
    'ID': 'cnm_p167_q1', 'Bank': 'cn-math', 'Language': 'en', 'ResponseType': 'numeric',
    'Question': 'Calculate: \\(1\\times3=?\\)', 'Choices': {}, 'Correct Answer': '3',
    'Solution': 'Multiply both the numerator and denominator of \\(\\frac{1}{2}\\) by 3. The new numerator is 3.',
    'Meta': {'SolutionSource': 'cn-math-taxonomy (AI-generated; not teacher reviewed)'}}


def api_response(text):
    return {'choices': [{'message': {'content': text}}]}


class TutorConnectionTests(unittest.TestCase):
    def account(self):
        return OpenAIConnection(Path('unused-work'), home=Path('unused-home'))

    def submission(self, selection, **kwargs):
        assessor, settings = MagicMock(), MagicMock()
        assessor.root = Path(__file__).resolve().parents[1]
        assessor.submission.return_value = (QUESTION, ATTEMPT['answer'], ATTEMPT['thoughts'])
        settings.inference_configured.return_value = True
        settings.inference_config.return_value = selection
        result = review_submission(assessor, settings, kwargs.pop('openai', MagicMock()), ATTEMPT, **kwargs)
        settings.inference_config.assert_called_once_with()
        return result

    def test_api_test_and_real_review_send_identical_structured_requests(self):
        with patch('practice_tutor.request', return_value=api_response(json.dumps(REVIEW))) as request, \
             patch('practice_tutor.question_images', return_value=([], [])):
            result = check_api(ModelConfig(tuple(API['bases']), API['model'], API['apiKey']))
            test_call = request.call_args
            review = self.submission(API)
            self.assertEqual(request.call_args, test_call)
        self.assertTrue(result['ready'])
        self.assertEqual(result['model'], API['model'])
        self.assertNotIn(API['apiKey'], json.dumps(result))
        self.assertTrue(review['answerCorrect'])
        self.assertEqual(test_call.args[1], '/v1/chat/completions')
        body = json.loads(test_call.args[2])
        self.assertEqual(body['model'], API['model'])
        self.assertEqual(body['messages'][0], {'role': 'system', 'content': INSTRUCTIONS})
        self.assertEqual(body['response_format'], {'type': 'json_object'})
        self.assertEqual(body['max_tokens'], 1000)
        self.assertIn('Return exactly four fields: category, answerCategory, coach, hint.', INSTRUCTIONS)
        self.assertEqual(SCHEMA['required'], ['category', 'answerCategory', 'coach', 'hint'])
        prompt = json.loads(body['messages'][1]['content'])
        self.assertEqual(prompt['reference']['question'], QUESTION['Question'])
        self.assertEqual(prompt['studentSubmission']['answer'], '4')
        self.assertEqual(prompt['attachedFiguresInOrder'], [])

    def test_codex_test_and_real_review_use_the_same_infer_adapter(self):
        account = self.account()
        with patch.object(account, 'infer', return_value=json.dumps(REVIEW)) as infer, \
             patch('practice_tutor.question_images', return_value=([], [])):
            result = account.test(ACCOUNT)
            test_call = infer.call_args
            self.submission({'provider': 'codex', **ACCOUNT}, openai=account)
            self.assertEqual(infer.call_args, test_call)
        self.assertTrue(result['ready'])
        self.assertEqual(result['effort'], 'xhigh')
        self.assertEqual(test_call.args[2], INSTRUCTIONS)
        self.assertEqual(test_call.args[3], SCHEMA)
        self.assertEqual(list(test_call.args[4]), [])

    def test_both_routes_reject_plain_text_incomplete_and_invalid_reviews(self):
        invalid = [
            'MATH_PRACTICE_OK',
            '{}',
            json.dumps({**REVIEW, 'category': 'partial', 'coach': ''}),
            json.dumps({**REVIEW, 'category': 'partial', 'coach': 'What justifies the sum?',
                        'hint': ' '.join(['word'] * 51)}),
        ]
        account = self.account()
        for text in invalid:
            with self.subTest(route='api', text=text), \
                 patch('practice_tutor.request', return_value=api_response(text)), \
                 self.assertRaises(AssessmentError) as raised:
                check_api(ModelConfig(tuple(API['bases']), API['model'], API['apiKey']))
            self.assertEqual(raised.exception.status, 502)
            with self.subTest(route='codex', text=text), \
                 patch.object(account, 'infer', return_value=text), \
                 self.assertRaises(AssessmentError) as raised:
                account.test(ACCOUNT)
            self.assertEqual(raised.exception.status, 502)
        # Invalid model output must not leave the existing test lock held.
        with patch.object(account, 'infer', return_value=json.dumps(REVIEW)):
            self.assertTrue(account.test(ACCOUNT)['ready'])

    def test_api_missing_review_content_is_rejected(self):
        for reply in ({}, {'choices': []}, api_response(None), api_response('')):
            with self.subTest(reply=reply), patch('practice_tutor.request', return_value=reply), \
                 self.assertRaises(AssessmentError) as raised:
                check_api(ModelConfig(tuple(API['bases']), API['model'], API['apiKey']))
            self.assertEqual(raised.exception.status, 502)

    def test_account_unavailable_and_running_test_behavior_is_preserved(self):
        account = self.account()
        with patch.object(account, 'status', return_value={'canTest': False, 'message': 'Sign in first.'}), \
             patch.object(account, '_generate') as generate, \
             self.assertRaisesRegex(AssessmentError, 'Sign in first'):
            account.test(ACCOUNT)
        generate.assert_not_called()
        with account._test_lock, self.assertRaises(AssessmentError) as raised:
            account.test(ACCOUNT)
        self.assertEqual(raised.exception.status, 409)

    def test_other_account_adapter_shares_request_and_validation(self):
        selection = {'provider': 'chatgpt', **ACCOUNT}
        transport, legacy = MagicMock(), MagicMock()
        transport.infer.return_value = json.dumps(REVIEW)
        with patch('practice_tutor.question_images', return_value=([], [])):
            result = check_tutor(selection, transport)
            test_call = transport.infer.call_args
            self.submission(selection, openai=legacy, chatgpt=transport)
        self.assertTrue(result['ready'])
        self.assertEqual(transport.infer.call_args, test_call)
        legacy.infer.assert_not_called()
        transport.infer.return_value = 'plain text is not a tutor review'
        with self.assertRaises(AssessmentError):
            check_tutor(selection, transport)


class TutorContractTests(unittest.TestCase):
    def test_useful_coach_is_visible_even_when_both_judgments_are_wrong(self):
        model = {'category': 'wrong', 'answerCategory': 'wrong',
                 'coach': 'You found half of 6. Which constant appears when you expand \\((x+3)^2\\)?',
                 'hint': 'Write the product \\((x+3)(x+3)\\) and identify its constant term.'}
        result = validate_review(json.dumps(model), known_category='wrong')
        self.assertEqual(result['coach'], model['coach'])
        self.assertEqual(result['clarification'], model['coach'])
        self.assertEqual(result['hint'], model['hint'])
        self.assertNotIn('9', result['coach'] + result['hint'])

    def test_hint_is_optional_and_complete_work_closes_without_one(self):
        partial = validate_review(json.dumps({**REVIEW, 'category': 'partial',
                                              'coach': 'Which calculation supports your answer?'}))
        self.assertEqual(partial['hint'], '')
        complete = validate_review(json.dumps({**REVIEW, 'hint': ' '.join(['unneeded'] * 51)}))
        self.assertEqual(complete['hint'], '')
        with self.assertRaises(AssessmentError):
            validate_review(json.dumps({'category': 'partial', 'answerCategory': 'correct',
                                        'clarification': 'Explain your step.', 'hint': ''}))

    def test_combined_length_is_bounded_for_english_unspaced_and_mixed_text(self):
        for coach, hint in [(' '.join(['word'] * 25), ' '.join(['word'] * 26)),
                            ('想' * 101, ''), ('想' * 51, ' '.join(['word'] * 25))]:
            with self.subTest(coach=coach), self.assertRaises(AssessmentError):
                validate_review(json.dumps({**REVIEW, 'category': 'partial', 'coach': coach, 'hint': hint}))
        chinese = validate_review(json.dumps({**REVIEW, 'category': 'partial', 'coach': '想' * 90}), language='zh')
        self.assertEqual(chinese['scriptCharacterCount'], 90)
        self.assertEqual(chinese['wordCount'], 0)
        mixed = validate_review(json.dumps({**REVIEW, 'category': 'partial',
                                           'coach': '想' * 50, 'hint': ' '.join(['word'] * 25)}))
        self.assertEqual(mixed['wordCount'], 25)

    def test_exact_override_replaces_contradictory_visible_and_hidden_text(self):
        result = validate_review(json.dumps({**REVIEW, 'answerCategory': 'wrong',
                                            'coach': 'Your final answer is incorrect.',
                                            'hint': 'Change your answer to five.'}), known_category='correct')
        self.assertEqual(result['category'], 'correct')
        self.assertEqual(result['answerCategory'], 'correct')
        self.assertEqual(result['coach'], 'Your explanation is correct.')
        self.assertEqual(result['hint'], '')
        self.assertEqual(result['modelJudgment']['answerCategory'], 'wrong')
        # Text itself must agree, even when the JSON label already agrees.
        result = validate_review(json.dumps({**REVIEW, 'coach': 'Your answer is wrong.'}), known_category='correct')
        self.assertNotIn('wrong', result['coach'])
        result = validate_review(json.dumps(REVIEW), known_category='wrong')
        self.assertEqual(result['category'], 'correct')
        self.assertEqual(result['answerCategory'], 'wrong')
        self.assertIn('final answer', result['coach'])

    def test_answer_form_feedback_cannot_be_overruled_by_praise_or_a_hint(self):
        form = 'Write your final answer as a decimal numeral rather than a fraction or expression.'
        result = validate_review(json.dumps({**REVIEW, 'hint': 'Keep the fraction.'}),
                                 known_category='partial', form_feedback=form)
        self.assertEqual(result['category'], 'correct')
        self.assertEqual(result['answerCategory'], 'partial')
        self.assertIsNone(result['answerCorrect'])
        self.assertEqual(result['coach'], form)
        self.assertEqual(result['hint'], '')
        chinese = validate_review(json.dumps(REVIEW), known_category='partial', form_feedback=form, language='zh-CN')
        self.assertIn('形式', chinese['coach'])

    def test_matching_partial_form_review_retains_specific_coaching(self):
        # Observed live: a correct part-whole explanation still needs a decimal.
        review = {'category': 'partial', 'answerCategory': 'partial',
                  'coach': 'You correctly identified one eighth of the sheet. Now calculate \\(1\\div8\\) to write your answer as a decimal.',
                  'hint': ''}
        result = validate_review(json.dumps(review), known_category='partial',
                                 form_feedback='Write your final answer as a decimal numeral rather than a fraction or expression.')
        self.assertEqual(result['coach'], review['coach'])
        self.assertEqual(result['hint'], '')
        self.assertEqual(result['answerCategory'], 'partial')
        self.assertIsNone(result['answerCorrect'])

    def test_turn_normalization_keeps_one_submission_and_seen_help_only(self):
        turn = {'revisionId': 'revision-2', 'action': 'revise', 'assistance': 'hint',
                'previous': {'answer': '3', 'thoughts': 'Half of 6 is 3.',
                             'coach': 'Which constant appears in the expansion?',
                             'openedHint': 'Write the product first.', 'audio': 'private', 'notebook': ['private']},
                'sentiment': 'private', 'notebook': ['private']}
        attempt = {'turn': turn}
        normalized = normalize_turn(attempt)
        self.assertEqual(normalized, attempt['turn'])
        self.assertEqual(normalize_turn(attempt), normalized)
        self.assertEqual(set(normalized), {'revisionId', 'action', 'assistance', 'previous'})
        self.assertEqual(set(normalized['previous']), {'answer', 'thoughts', 'coach', 'openedHint'})
        prompt = json.loads(review_prompt(QUESTION, '4', 'I revised my sum.', 'partial', 'correct', 'correct', turn=normalized))
        self.assertEqual(prompt['turn'], normalized)
        self.assertNotIn('private', json.dumps(prompt))
        self.assertIsNone(normalize_turn({}))
        self.assertEqual(json.loads(review_prompt(QUESTION, '4', 'A step.', 'partial', 'correct', 'correct'))['turn']['assistance'], 'unknown')

    def test_turn_invalid_types_and_unbounded_history_are_rejected(self):
        valid = {'revisionId': 'r1', 'action': 'submit', 'assistance': 'none', 'previous': None}
        invalid = [[], {'revisionId': ''}, {'revisionId': 'x' * 129}, {'action': 'retry'}, {'assistance': 'independent'},
                   {'previous': []}, {'previous': {'answer': '3', 'thoughts': 'a', 'coach': '', 'openedHint': True}},
                   {'previous': {'answer': '3', 'thoughts': 'a' * 12001, 'coach': '', 'openedHint': None}}]
        for change in invalid:
            turn = {**valid, **change} if isinstance(change, dict) else change
            with self.subTest(turn=turn), self.assertRaises(AssessmentError) as raised:
                normalize_turn({'turn': turn})
            self.assertEqual(raised.exception.status, 400)
        with self.assertRaises(AssessmentError):
            normalize_turn([])

    def test_reference_provenance_and_known_conflict_follow_the_displayed_task(self):
        multiplication = LEGACY_MULTIPLICATION
        with patch('practice_tutor.criterion_for_prompt', return_value='Explain fraction equivalence.'):
            prompt = json.loads(review_prompt(multiplication, '3', 'I multiplied.', 'partial', 'correct', 'correct'))
        self.assertEqual(prompt['reference']['question'], multiplication['Question'])
        self.assertEqual(prompt['reference']['solution'], '')
        self.assertIsNone(prompt['reviewedCriterion'])
        self.assertIn('Reviewed mismatch', prompt['reference']['solutionOmittedReason'])
        self.assertIn('AI-generated', prompt['reference']['solutionProvenance']['source'])
        repaired = {**multiplication, 'Solution': 'Multiply one by three to obtain three.'}
        self.assertEqual(reference_solution(repaired)['text'], repaired['Solution'])
        with patch('practice_tutor.criterion_for_prompt', return_value='Complete the square.'):
            prompt = json.loads(review_prompt(QUESTION, '4', 'I added.', 'partial', 'correct', 'correct'))
        self.assertEqual(prompt['reviewedCriterion'], 'Complete the square.')
        self.assertEqual(prompt['practiceLanguage'], 'en')

    def test_assessment_uses_the_same_filtered_reference_in_both_decision_modes(self):
        repaired = {**LEGACY_MULTIPLICATION, 'Solution': 'Multiplying 1 by 3 gives 3.'}
        attempt = {'questionId': LEGACY_MULTIPLICATION['ID'], 'answer': '3',
                   'thoughts': 'I multiplied one by three to get three.'}
        for mode in ('isolated', 'shared'):
            for question in (LEGACY_MULTIPLICATION, repaired):
                assessor = StudentAssessment(ModelConfig(('https://provider.example/v1',), 'fixture-model'))
                assessor.decision_mode = mode
                observations = lambda context, rubrics: [{'id': key, 'code': 'correct'} for key in rubrics]
                with self.subTest(mode=mode, solution=question['Solution']), \
                     patch.object(assessor, '_question', return_value=question), \
                     patch.object(assessor, '_decide', side_effect=observations) as decide:
                    result = assessor.assess(attempt)
                self.assertEqual(result['category'], 'correct')
                self.assertEqual(result['answerCategory'], 'correct')
                for call in decide.call_args_list:
                    context = call.args[0]
                    self.assertIn('The displayed question and choices define the task.', context)
                    self.assertIn('solutionProvenance', context)
                    self.assertNotIn('\\\\frac{1}{2}', context)
                    if question is LEGACY_MULTIPLICATION:
                        self.assertIn('"referenceSolution": ""', context)
                        self.assertIn('Reviewed mismatch', context)
                    else:
                        self.assertIn(repaired['Solution'], context)

    def test_instructions_do_not_supply_the_pilot_answer_or_desired_coaching(self):
        for text in ('x^2+6x', 'half of 6', '9, because the last term is 3^2', 'Which constant appears'):
            self.assertNotIn(text, INSTRUCTIONS)
        self.assertIn('2(x+3)', INSTRUCTIONS)

    def test_provider_requests_preserve_selected_path_and_standard_with_bound_routes(self):
        root = Path(__file__).resolve().parents[1]
        question = json.loads((root / 'cn-math-bank/questions/cnm_090_q3.json').read_text(encoding='utf-8'))
        question.pop('KnowledgeGraph', None)
        temporary = tempfile.TemporaryDirectory(prefix='tutor-provider-graph-')
        self.addCleanup(temporary.cleanup)
        runtime_root = Path(temporary.name)
        source = runtime_root / 'knowledge-graph/source'
        source.mkdir(parents=True)
        question_folder = runtime_root / 'cn-math-bank/questions'
        question_folder.mkdir(parents=True)
        (question_folder / (question['ID'] + '.json')).write_text(json.dumps(question), encoding='utf-8')
        nodes = [{'id': node_id, 'name': name, 'description': name, 'criteria': [name],
                  'level': 'Grade 7', 'kind': 'procedure', 'aliases': [], 'reviewStatus': 'fixture_reviewed'}
                 for node_id, name in [('cnm_089', 'Solve by substitution'), ('cnm_090', 'Solve by elimination')]]
        mapping = {'questionId': question['ID'], 'bank': question['Bank'],
                   **question_fingerprint(question, runtime_root), 'status': 'mapped',
                   'reviewStatus': 'fixture_reviewed', 'assessedIds': ['cnm_090'], 'supportIds': [],
                   'routes': [{'id': 'elimination', 'label': 'Eliminate a variable', 'nodeIds': ['cnm_090']},
                              {'id': 'substitution', 'label': 'Substitute a variable', 'nodeIds': ['cnm_089']}],
                   'sourceTopicAgreement': 'fixture', 'flags': [], 'rationale': 'The task is a two-variable linear system.',
                   'answerCheck': {}, 'reviews': []}
        curricula = {'schemaVersion': 1, 'layers': [
            {'id': layer, 'label': layer, 'source': 'Fixture curriculum', 'revision': 'one',
             'placementMeaning': 'Fixture placement, not learner knowledge.',
             'nodes': [{'id': node_id, 'label': node_id, 'description': 'Fixture source scope',
                        'placement': {'grade': 8}} for node_id in ('standard', 'foundation', 'unrelated')],
             'relationships': [{'id': 'native-preparation', 'fromId': 'standard', 'toId': 'foundation',
                                'relation': 'supports'}]}
            for layer in ('CN', 'US')]}
        alignments = [{'id': layer + '-elimination', 'nodeId': 'cnm_090', 'layer': layer,
                       'sourceNodeId': 'standard', 'relation': 'exact', 'status': 'accepted',
                       'reason': 'Fixture source matches elimination.', 'reviewStatus': 'fixture_reviewed'}
                      for layer in ('CN', 'US')]
        relationships = [{'id': 'math-preparation', 'nodeId': 'cnm_090', 'prerequisiteId': 'cnm_089',
                          'relation': 'prepares', 'methodId': None, 'scope': 'Fixture system methods',
                          'reason': 'Substitution can prepare work with systems.', 'status': 'accepted',
                          'reviewStatus': 'fixture_reviewed', 'original': {}, 'reviews': []}]
        for name, value in [('metadata', {'version': 'provider-test-v1'}), ('nodes', nodes),
                            ('relationships', relationships), ('curricula', curricula), ('alignments', alignments)]:
            (source / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
        (source / 'mappings.jsonl').write_text(json.dumps(mapping) + '\n', encoding='utf-8')
        build_database(runtime_root)
        thoughts = 'I express y in terms of x and substitute into the other equation.'
        attempt = {**ATTEMPT, 'questionId': question['ID'], 'answer': '2,3', 'thoughts': thoughts}
        paths = (('ailleo', 'cnm_090'), ('CN', 'standard'), ('US', 'standard'),
                 ('CN', 'unrelated'), ('US', 'unrelated'))
        for provider, layer, selected in ((p, layer, selected) for p in ('api', 'codex', 'chatgpt')
                                           for layer, selected in paths):
            with self.subTest(provider=provider, layer=layer, selected=selected):
                assessor, settings, account = MagicMock(), MagicMock(), MagicMock()
                assessor.root = runtime_root
                assessor.submission.return_value = (question, attempt['answer'], thoughts)
                settings.inference_configured.return_value = True
                settings.inference_config.return_value = API if provider == 'api' else {'provider': provider, **ACCOUNT}
                account.infer.return_value = json.dumps(REVIEW)
                selected_attempt = {**attempt, 'curriculumLayer': layer, 'curriculumNodeId': selected}
                with patch('practice_tutor.request', return_value=api_response(json.dumps(REVIEW))) as request:
                    review_submission(assessor, settings, account, selected_attempt, chatgpt=account)
                wire = json.loads(request.call_args.args[2])['messages'][1]['content'] if provider == 'api' else account.infer.call_args.args[1]
                prompt = json.loads(wire)
                self.assertEqual(prompt['studentSubmission']['reasoning'], thoughts)
                context = prompt['teachingContext']
                self.assertIsNone(context['grade'])
                self.assertEqual(context['layer'], layer)
                self.assertEqual(context['contextSource'], 'central_graph')
                self.assertEqual(context['knowledgeGraph']['binding']['status'], 'current')
                self.assertEqual({route['id'] for route in context['knowledgeGraph']['routes']},
                                 {'elimination', 'substitution'})
                self.assertEqual({node['id'] for node in context['knowledgeGraph']['nodes']}, {'cnm_089', 'cnm_090'})
                self.assertTrue(all('level' not in node for node in context['knowledgeGraph']['nodes']))
                if layer == 'ailleo':
                    selection = context['knowledgeGraph']['curriculumSelection']
                    self.assertEqual([e['id'] for e in context['knowledgeGraph']['edges']], ['math-preparation'])
                    self.assertNotIn('curriculumContext', context['knowledgeGraph'])
                else:
                    native = context['knowledgeGraph']['curriculumContext']
                    selection = native['selection']
                    self.assertEqual(context['knowledgeGraph']['edges'], [])
                    self.assertEqual(native['layer'], layer)
                    self.assertEqual({e['id'] for n in native['neighborhoods'] for e in n['relationships']},
                                     {'native-preparation'})
                self.assertEqual(selection['nodeId'], selected)
                self.assertEqual(selection['status'], 'unrelated_to_question' if selected == 'unrelated' else 'matched')
                self.assertNotIn('sourceTopicId', context)
                self.assertNotIn('taskTopicIds', context)
                self.assertNotIn('relevanceHints', context)
                self.assertNotIn('studentRoute', context)

    def test_production_review_echoes_the_frozen_revision(self):
        assessor, settings, transport = MagicMock(), MagicMock(), MagicMock()
        assessor.submission.return_value = (QUESTION, '4', 'I added two and two.')
        settings.inference_configured.return_value = True
        settings.inference_config.return_value = {'provider': 'chatgpt', **ACCOUNT}
        transport.infer.return_value = json.dumps(REVIEW)
        attempt = {**ATTEMPT, 'turn': {'revisionId': 'frozen-2', 'action': 'revise',
                                     'assistance': 'coach', 'previous': None}}
        with patch('practice_tutor.question_images', return_value=([], [])):
            result = review_submission(assessor, settings, MagicMock(), attempt, chatgpt=transport)
        self.assertEqual(result['revisionId'], 'frozen-2')
        self.assertEqual(json.loads(transport.infer.call_args.args[1])['turn']['revisionId'], 'frozen-2')
        settings.inference_configured.return_value = False
        self.assertEqual(review_submission(assessor, settings, MagicMock(), attempt)['revisionId'], 'frozen-2')


if __name__ == '__main__':
    unittest.main()
