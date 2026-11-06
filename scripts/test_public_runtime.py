"""Portable runtime checks with temporary records and synthetic model responses."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request

from connection_settings import ConnectionSettings, SettingsError
import launch_math_practice as launcher
from model_connections import model_status, test_inference, test_speech
from practice_tutor import review_submission
from serve_math_practice import ENGINE_VERSION, Handler, ThreadingHTTPServer, engine_instance
from student_assessment import AssessmentError, ModelConfig, StudentAssessment


QUESTION = {'ID': 'cnm_p001_q1', 'Bank': 'cn-math', 'ResponseType': 'numeric',
            'Question': 'What is 2 + 2?', 'Choices': {}, 'Correct Answer': '4',
            'Solution': 'Add two and two to get four.'}
ATTEMPT = {'questionId': QUESTION['ID'], 'answer': '4', 'thoughts': 'I added two and two.'}


class RuntimeFixture:
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.settings = ConnectionSettings(self.root / 'config.json')
        self.questions = self.root / 'questions'
        self.questions.mkdir()
        (self.questions / (QUESTION['ID'] + '.json')).write_text(json.dumps(QUESTION), encoding='utf-8')
        self.assessor = StudentAssessment(ModelConfig(), cn_bank_root=self.questions)

    def tearDown(self):
        self.temporary.cleanup()
        self.environment.stop()


class RuntimeTests(RuntimeFixture, unittest.TestCase):
    def shared(self, **overrides):
        return {'setup': {'mode': 'single', 'provider': 'custom'}, 'shared': {
            'bases': ['https://provider.example/v1'], 'speechModel': 'speech-test',
            'textModel': 'text-test', 'apiKey': 'shared-secret', 'useTutor': False, **overrides}}

    def test_single_provider_round_trip_and_saved_key_reuse(self):
        public = self.settings.save(self.shared())
        self.assertEqual(public['setup']['mode'], 'single')
        self.assertTrue(public['speech']['configured'])
        self.assertEqual(public['decision']['protocol'], 'chat')
        self.assertFalse(public['inference']['configured'])
        self.assertNotIn('shared-secret', json.dumps(public))
        restarted = ConnectionSettings(self.settings.path)
        self.assertEqual(restarted.public()['setup'], public['setup'])
        patch_value = self.shared(apiKey='', useTutor=True)
        self.assertTrue(restarted.compare_file(patch_value)['different'])
        restarted.save(patch_value)
        self.assertEqual(restarted.inference_config()['apiKey'], 'shared-secret')
        self.assertEqual(restarted.decision_config().api_key, 'shared-secret')
        self.assertFalse(restarted.compare_file(patch_value)['different'])

    def test_empty_single_setup_matches_saved_empty_connections(self):
        self.settings.save({})
        value = self.shared(bases=[], speechModel='', textModel='', apiKey='')
        value['setup']['provider'] = ''
        self.assertFalse(self.settings.compare_file(value)['different'])

    def test_changing_provider_does_not_forward_the_previous_key(self):
        self.settings.save(self.shared())
        changed = self.shared(bases=['https://another-provider.example/v1'], apiKey='')
        self.assertEqual(self.settings.speech_config(changed).api_key, '')
        changed['setup']['provider'] = 'openai'
        with self.assertRaisesRegex(SettingsError, 'API key'):
            self.settings.save(changed)
        self.assertEqual(self.settings.speech_config().api_key, 'shared-secret')

    def test_separate_mode_and_explicit_key_reuse(self):
        self.settings.save(self.shared())
        self.settings.save({'setup': {'mode': 'separate'}})
        self.assertEqual(ConnectionSettings(self.settings.path).public()['setup']['mode'], 'separate')
        patch_value = {'inference': {'provider': 'api', 'bases': ['https://provider.example/v1'],
                                     'model': 'text-test', 'keyFrom': 'decision'}}
        self.settings.save(patch_value)
        self.assertEqual(self.settings.inference_config()['apiKey'], 'shared-secret')
        patch_value['inference']['bases'] = ['https://another-provider.example']
        with self.assertRaises(SettingsError):
            self.settings.save(patch_value)

    def test_chat_learning_signals_have_evidence_without_invented_probabilities(self):
        assessor = StudentAssessment(ModelConfig(('https://provider.example/v1',), 'text-test', 'test-key', 'chat'), cn_bank_root=self.questions)
        observations = {'confidence': {'code': 'uncertain', 'evidence': 'The student says "I am unsure".'},
                        'reasoning': {'code': 'incomplete', 'evidence': 'No approach is explained.'},
                        'engagement': {'code': 'unclear', 'evidence': 'No engagement cue is expressed.'}}
        reply = {'choices': [{'message': {'content': json.dumps(observations)}}]}
        with patch('model_connections.request', return_value=reply) as request:
            result = assessor.learning_signals({'questionId': QUESTION['ID'], 'transcript': 'I am unsure.'})
        self.assertEqual(len(result['signals']), 3)
        self.assertEqual(result['signals'][0]['code'], 'uncertain')
        self.assertNotIn('score', result['signals'][0])
        self.assertNotIn('probabilities', json.dumps(result))
        self.assertEqual(request.call_args.args[1], '/v1/chat/completions')
        self.assertIn('I am unsure.', request.call_args.args[2].decode())
        observations['confidence']['code'] = 'happy'
        reply['choices'][0]['message']['content'] = json.dumps(observations)
        with patch('model_connections.request', return_value=reply), self.assertRaises(AssessmentError):
            assessor.learning_signals({'questionId': QUESTION['ID'], 'transcript': 'I am unsure.'})

    def test_defaults_and_partial_configuration_are_independent(self):
        public = self.settings.public()
        for role in ('decision', 'speech', 'inference'):
            self.assertFalse(public[role]['configured'])
            self.assertEqual(public[role]['bases'], [])
            self.assertEqual(public[role]['model'], '')
        self.assertEqual(public['inference']['provider'], 'api')
        self.settings.save({'decision': {'bases': ['https://decision.example/v1'], 'model': 'my-decision', 'apiKey': 'test-secret'}})
        restarted = ConnectionSettings(self.settings.path)
        self.assertTrue(restarted.decision_config().configured)
        self.assertFalse(restarted.speech_config().configured)
        self.assertFalse(restarted.inference_configured())
        self.assertNotIn('test-secret', json.dumps(restarted.public()))
        restarted.save({'speech': {'bases': ['https://speech.example'], 'model': ''}})
        self.assertFalse(restarted.speech_config().configured)
        restarted.save({'decision': {'bases': [], 'model': ''}})
        self.assertFalse(restarted.decision_config().configured)
        restarted.save({'inference': {'provider': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'xhigh'}})
        self.assertTrue(restarted.inference_configured())

    def test_role_keys_never_inherit_from_other_roles_or_legacy_files(self):
        with patch.dict(os.environ, {'DECISION_API_KEY': 'decision-only'}):
            settings = ConnectionSettings(self.root / 'other.json')
        self.assertEqual(settings.decision_config().api_key, 'decision-only')
        self.assertEqual(settings.speech_config().api_key, '')
        with patch.dict(os.environ, {'JEV_BASE_URL': 'https://legacy.example', 'JEV_API_KEY': 'legacy-key'}):
            self.assertEqual(ModelConfig.from_environment(), ModelConfig())

    def test_no_model_paths_do_not_contact_services_or_accounts(self):
        with patch('student_assessment.OPENER.open', side_effect=AssertionError('No network request expected')):
            for status in (self.assessor.status(), model_status(ModelConfig()),
                           test_speech(ModelConfig()), test_inference(ModelConfig()),
                           self.settings.test_decision({})):
                self.assertFalse(status['configured'])
                self.assertFalse(status['ready'])
                self.assertEqual(status['label'], 'Not configured')
            result = self.assessor.assess(ATTEMPT)
            self.assertEqual(result['answerCategory'], 'correct')
            self.assertTrue(result['answerCorrect'])
            self.assertEqual(result['category'], 'cannot_judge')
            self.assertFalse(result['decisionConfigured'])
            self.assertFalse(result['modelUsed'])
            self.assertEqual(result['decisionRequests'], 0)
            signals = self.assessor.learning_signals({'questionId': QUESTION['ID'], 'transcript': 'I will try adding.'})
            self.assertEqual(signals['signals'], [])
        account = MagicMock()
        with patch('practice_tutor.question_images', side_effect=AssertionError('No image conversion expected')):
            result = review_submission(self.assessor, self.settings, account, ATTEMPT)
        self.assertFalse(result['configured'])
        self.assertEqual(result['answerCategory'], 'correct')
        account.infer.assert_not_called()

    def test_configured_decision_and_inference_still_use_selected_models(self):
        assessor = StudentAssessment(ModelConfig(('https://decision.example',), 'my-model'), cn_bank_root=self.questions)
        judgment = lambda rubric: [{'id': rubric, 'code': 'correct'}]
        with patch.object(assessor, '_decide', side_effect=[judgment('correctness'), judgment('answer_correctness')]) as decide:
            result = assessor.assess(ATTEMPT)
        self.assertEqual(result['category'], 'correct')
        self.assertTrue(result['decisionConfigured'])
        self.assertTrue(result['modelUsed'])
        self.assertEqual(decide.call_count, 2)
        self.settings.save({'inference': {'provider': 'api', 'bases': ['https://inference.example/v1'], 'model': 'my-inference'}})
        reply = {'choices': [{'message': {'content': json.dumps({'category': 'correct', 'answerCategory': 'correct', 'coach': 'Your explanation is correct.', 'hint': ''})}}]}
        with patch('practice_tutor.request', return_value=reply) as request:
            result = review_submission(assessor, self.settings, MagicMock(), {**ATTEMPT, 'category': 'cannot_judge', 'answerCategory': 'correct'})
        self.assertTrue(result['inferenceConfigured'])
        self.assertEqual(request.call_args.args[0].model, 'my-inference')
        self.assertEqual(request.call_args.args[1], '/v1/chat/completions')

    def test_invalid_nonempty_configuration_is_rejected(self):
        for section in ({'bases': ['file:///secret']}, {'model': '../invalid'}, {'bases': ['https://user:pass@example.test']}):
            with self.subTest(section=section), self.assertRaises(SettingsError):
                self.settings.save({'decision': section})

    def test_engine_reuse_requires_same_distribution_and_checkout(self):
        response = {'application': 'math-practice', 'pid': 123, 'version': ENGINE_VERSION,
                    'instance': engine_instance(launcher.ROOT)}
        def probe(value):
            handle = MagicMock()
            handle.__enter__.return_value = io.BytesIO(json.dumps(value).encode())
            with patch.object(launcher.OPENER, 'open', return_value=handle):
                return launcher.engine('http://127.0.0.1:8877')
        self.assertEqual(probe(response), response)
        for modified in ({'version': 'legacy'}, {'instance': 'other-checkout'}):
            self.assertIsNone(probe({**response, **modified}))
        self.assertIsNone(probe({'application': 'math-practice', 'pid': 123}))

    def test_launcher_opens_practice_without_automatic_model_tests(self):
        self.settings.save({})
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(b'{}')
        with patch('connection_settings.ConnectionSettings', return_value=self.settings), \
             patch.object(launcher, 'engine', return_value={'pid': 123}), \
             patch.object(launcher.OPENER, 'open', return_value=response) as request, \
             patch.object(launcher.webbrowser, 'open') as browser:
            result = launcher.launch(open_browser=True)
        self.assertEqual(result['url'], 'http://127.0.0.1:8877/math-practice/')
        browser.assert_called_once_with(result['url'])
        self.assertEqual(request.call_count, 1)
        self.assertTrue(request.call_args.args[0].full_url.endswith('/api/settings/reload'))


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class HttpRuntimeTests(RuntimeFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.server.settings = self.settings
        self.server.assessor = self.assessor
        self.server.openai = MagicMock()
        self.server.chatgpt = MagicMock()
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()
        super().tearDown()

    def request(self, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.load(exc)

    def test_http_no_model_assessment_status_and_tutor(self):
        for role in ('decision', 'speech', 'inference'):
            code, value = self.request('/api/status/' + role)
            self.assertEqual(code, 200)
            self.assertFalse(value['configured'])
        code, value = self.request('/api/assessment', ATTEMPT)
        self.assertEqual(code, 200)
        self.assertTrue(value['answerCorrect'])
        self.assertFalse(value['decisionConfigured'])
        self.assertFalse(value['inferenceConfigured'])
        code, value = self.request('/api/settings/inference/test', {})
        self.assertEqual(code, 200)
        self.assertFalse(value['configured'])
        code, value = self.request('/api/tutor', ATTEMPT)
        self.assertEqual(code, 200)
        self.assertFalse(value['configured'])
        self.server.openai.status.assert_not_called()
        self.server.openai.infer.assert_not_called()

    def test_revision_bound_graph_record_and_empty_reasoning_at_http_boundary(self):
        item = 'cnm_221_q2'
        real_item = Path(__file__).resolve().parents[1] / 'cn-math-bank' / 'questions' / (item + '.json')
        (self.questions / real_item.name).write_bytes(real_item.read_bytes())
        turn = {'revisionId': 'test-first', 'assistance': 'none', 'action': 'submit', 'previous': None}
        attempt = {'bank': 'cn-math', 'questionId': item, 'answer': '9', 'thoughts': '', 'turn': turn}
        with patch('student_assessment.StudentAssessment._decide', side_effect=AssertionError('Blank work must skip inference')):
            code, assessed = self.request('/api/assessment', attempt)
        self.assertEqual(code, 200)
        self.assertEqual(assessed['category'], 'cannot_judge')
        self.assertEqual(assessed['answerCategory'], 'correct')
        self.assertEqual(assessed['graphEvidence']['status'], 'unobserved')
        self.assertEqual(assessed['graphEvidence']['observationReason'], 'blank_reasoning')
        self.assertIn(item, self.request('/api/status/decision')[1]['localEvidenceItems'])
        self.assertEqual(assessed['graphEvidence']['revisionId'], turn['revisionId'])
        self.assertEqual(self.request('/api/assessment', {**attempt, 'bank': 'amc'})[0], 400)
        self.assertEqual(self.request('/api/assessment', {**attempt, 'turn': {'revisionId': []}})[0], 400)
        self.assertNotIn('graphEvidence', self.request('/api/assessment', {**ATTEMPT, 'bank': 'cn-math', 'turn': turn})[1])
        self.assertNotIn('graphEvidence', self.request('/api/assessment', {key: val for key, val in attempt.items() if key != 'turn'})[1])

    def test_http_engine_identity_and_independent_settings(self):
        code, value = self.request('/api/engine')
        self.assertEqual(code, 200)
        self.assertEqual(value['version'], ENGINE_VERSION)
        self.assertEqual(value['instance'], engine_instance())
        code, value = self.request('/api/settings', {'speech': {'bases': ['https://speech.example'], 'model': 'my-asr', 'apiKey': 'speech-secret'}})
        self.assertEqual(code, 200)
        self.assertTrue(value['speech']['configured'])
        self.assertFalse(value['decision']['configured'])
        self.assertFalse(value['inference']['configured'])
        self.assertNotIn('speech-secret', json.dumps(value))

    def test_chatgpt_uses_the_chosen_model_for_testing_and_practice(self):
        custom = {'provider': 'api', 'bases': ['https://tutor.example'], 'model': 'local-tutor', 'apiKey': 'test-key'}
        self.settings.save({'inference': custom})
        plan = {'inference': {'provider': 'chatgpt', 'model': 'plan-tutor'}}
        self.server.chatgpt.status.return_value = {'state': 'signed_in', 'canTest': True, 'message': 'Signed in.'}
        self.server.chatgpt.infer.return_value = json.dumps({'category': 'correct', 'answerCategory': 'correct',
                                                             'hint': '', 'coach': 'Your explanation is correct.'})
        self.assertEqual(self.request('/api/connections/chatgpt')[1]['state'], 'signed_in')
        self.server.chatgpt.infer.assert_not_called()
        self.assertTrue(self.request('/api/settings/inference/test', plan)[1]['ready'])
        self.assertEqual(self.settings.inference_config()['provider'], 'api')
        status, saved = self.request('/api/settings', plan)
        self.assertEqual(status, 200)
        self.assertNotIn('test-key', json.dumps(saved))
        self.assertEqual(saved['inference']['modelByProvider']['api'], 'local-tutor')
        self.assertTrue(self.request('/api/status/inference')[1]['ready'])
        code, review = self.request('/api/tutor', {**ATTEMPT, 'category': 'cannot_judge', 'answerCategory': 'correct'})
        self.assertEqual(code, 200)
        self.assertEqual(review['category'], 'correct')
        for call in self.server.chatgpt.infer.call_args_list:
            self.assertEqual(call.args[0]['model'], 'plan-tutor')
            self.assertNotIn('test-key', json.dumps(call.args[0]))
        self.assertEqual(self.server.chatgpt.infer.call_count, 2)
        self.server.openai.infer.assert_not_called()
        self.assertEqual(self.request('/api/settings/reload', {})[1]['inference']['provider'], 'chatgpt')
        self.assertFalse(self.request('/api/settings/compare', plan)[1]['different'])
        self.settings.save({'inference': {'provider': 'api', 'model': 'local-tutor'}})
        self.assertEqual(self.settings.inference_config()['apiKey'], 'test-key')

    def test_account_actions_are_explicit_and_local(self):
        for action, method in (('login', 'start_login'), ('cancel', 'cancel_login'), ('disconnect', 'sign_out')):
            handler = getattr(self.server.chatgpt, method)
            handler.return_value = {'state': 'signed_out'}
            self.assertEqual(self.request('/api/connections/chatgpt/' + action, {})[0], 200)
            handler.assert_called_once_with()
        self.assertEqual(self.request('/api/connections/chatgpt/login', {'clientId': 'saved-account'})[0], 200)
        self.server.chatgpt.start_login.assert_called_with(client_id='saved-account')
        self.assertEqual(self.request('/api/connections/chatgpt/login', {'newAccount': True})[0], 200)
        self.server.chatgpt.start_login.assert_called_with(new_account=True)
        self.assertEqual(self.request('/api/connections/chatgpt/login', {'newAccount': 'yes'})[0], 400)
        self.server.chatgpt.infer.assert_not_called()

    def test_private_and_legacy_paths_are_not_served(self):
        for path in ('/math-practice/config.json', '/scripts/student_assessment.py',
                     '/math-practice/amc-bank.js', '/question%20bank/figures/example.png'):
            self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request('/api/assessment', {**ATTEMPT, 'questionId': '9999_AMC_8_Q01'})[0], 404)

    def test_amc_legacy_and_frozen_turn_submissions_share_the_same_bank(self):
        question = self.assessor._question('2023_AMC_8_Q01')
        attempt = {'questionId': question['ID'], 'answer': question['Correct Answer'], 'thoughts': 'I evaluated each group first.'}
        for extra in ({}, {'bank': 'amc', 'turn': {'revisionId': 'amc-current', 'action': 'submit',
                                                'assistance': 'none', 'previous': None}}):
            code, result = self.request('/api/assessment', {**attempt, **extra})
            self.assertEqual(code, 200)
            self.assertEqual(result['answerCategory'], 'correct')
            self.assertNotIn('graphEvidence', result)
        self.server.chatgpt.infer.assert_not_called()

    def test_pilot_evidence_binds_to_the_current_revision_and_presubmission_help(self):
        source = Path(__file__).resolve().parents[1] / 'cn-math-bank/questions/cnm_221_q2.json'
        question = json.loads(source.read_text(encoding='utf-8'))
        (self.questions / source.name).write_text(json.dumps(question), encoding='utf-8')
        attempt = {'bank': 'cn-math', 'questionId': question['ID'], 'answer': '9',
                   'thoughts': 'The constant is 3 squared, so 3^2 = 9.',
                   'turn': {'revisionId': 'coached-revision', 'action': 'revise', 'assistance': 'coach',
                            'previous': {'answer': '3', 'thoughts': 'I added 3 because half of 6 is 3.',
                                         'coach': 'Which constant appears when you expand the square?', 'openedHint': None}}}
        code, result = self.request('/api/assessment', attempt)
        self.assertEqual(code, 200)
        evidence = result['graphEvidence']
        self.assertEqual(evidence['revisionId'], 'coached-revision')
        self.assertEqual(evidence['bank'], attempt['bank'])
        self.assertEqual(evidence['questionId'], question['ID'])
        self.assertEqual(evidence['assistance'], 'coach')
        self.assertEqual(evidence['status'], 'demonstrated')
        self.assertIn(evidence['quote'], attempt['thoughts'])
        self.assertTrue(evidence['shadow'])
        self.server.chatgpt.infer.assert_not_called()

    def test_tutor_receives_one_prior_submission_without_speech_or_notebook_fields(self):
        reply = json.dumps({'category': 'partial', 'answerCategory': 'correct',
                            'coach': 'Which calculation supports that total?', 'hint': ''})
        prior = {'answer': '3', 'thoughts': 'I counted three.', 'coach': 'What did you count?',
                 'openedHint': 'Count both pairs.', 'rawAudio': 'private-audio', 'notebook': ['older work']}
        attempt = {**ATTEMPT, 'bank': 'cn-math', 'category': 'partial', 'answerCategory': 'correct',
                   'originalSpeech': {'transcript': 'Original private speech'},
                   'turn': {'revisionId': 'current-turn', 'action': 'revise', 'assistance': 'hint', 'previous': prior}}
        for provider in ('chatgpt', 'api'):
            with self.subTest(provider=provider):
                self.settings.save({'inference': {'provider': provider, 'model': 'synthetic-tutor',
                                                 'bases': ['https://synthetic.invalid'], 'apiKey': 'synthetic-key'}})
                self.server.chatgpt.infer.return_value = reply
                with patch('practice_tutor.request', return_value={'choices': [{'message': {'content': reply}}]}) as transport:
                    code, result = self.request('/api/tutor', attempt)
                self.assertEqual(code, 200)
                self.assertEqual(result['revisionId'], 'current-turn')
                if provider == 'chatgpt':
                    prompt = json.loads(self.server.chatgpt.infer.call_args.args[1])
                else:
                    wire = json.loads(transport.call_args.args[2])
                    prompt = json.loads(wire['messages'][1]['content'])
                self.assertEqual(prompt['turn']['previous']['openedHint'], prior['openedHint'])
                self.assertEqual(set(prompt['turn']['previous']), {'answer', 'thoughts', 'coach', 'openedHint'})
                self.assertNotIn('private-audio', json.dumps(prompt))
                self.assertNotIn('older work', json.dumps(prompt))
                self.assertNotIn('Original private speech', json.dumps(prompt))


if __name__ == '__main__':
    unittest.main()
