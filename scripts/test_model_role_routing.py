"""HTTP role separation with synthetic local responses and a mocked Codex account."""
import io
import json
import threading
import unittest
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request
import wave

from serve_math_practice import ThreadingHTTPServer, engine_instance
from student_assessment import ModelConfig, StudentAssessment
from test_public_runtime import ATTEMPT, QUESTION, QuietHandler, RuntimeFixture


LOCAL_DECISION = {'bases': ['http://127.0.0.1:5611'], 'model': 'd3-mini', 'protocol': 'systemone'}
LOCAL_SPEECH = {'bases': ['http://127.0.0.1:5000/v1'], 'model': 'qwen3-asr'}
CODEX = {'provider': 'codex', 'model': 'gpt-6.1-sol', 'effort': 'xhigh'}


def systemone_reply(payload):
    return {'answers': {name: {'probabilities': {key: int(index == 0)
                                               for index, key in enumerate(question['criteria'])}}
                        for name, question in payload['questions'].items()}}


class ModelRoleRoutingTests(RuntimeFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.assessor = StudentAssessment(ModelConfig(), cn_bank_root=self.questions, root=self.root)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.server.settings = self.settings
        self.server.assessor = self.assessor
        self.server.openai = MagicMock()
        self.server.chatgpt = MagicMock()
        self.server.openai.infer.return_value = json.dumps({
            'category': 'correct', 'answerCategory': 'correct',
            'coach': 'You correctly added both pairs.', 'hint': ''})
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()
        super().tearDown()

    def configure(self, *, inference_math=True):
        value = {'decision': LOCAL_DECISION, 'speech': LOCAL_SPEECH, 'inference': CODEX}
        if inference_math:
            value['mathAssessment'] = 'inference'
        self.settings.save(value)

    def request(self, path, body=None, *, audio=None):
        data = audio if audio is not None else None if body is None else json.dumps(body).encode()
        content_type = 'audio/wav' if audio is not None else 'application/json'
        request = urllib.request.Request(self.base + path, data=data, headers={'Content-Type': content_type})
        try:
            with self.opener.open(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.load(exc)

    def test_original_speech_signals_use_only_local_d3_rubrics(self):
        self.configure()
        transcript = 'I am unsure, but I want to keep trying.'
        def reply(config, route, data, content_type, timeout=None):
            self.assertEqual(config.model, 'd3-mini')
            self.assertEqual(config.bases, tuple(LOCAL_DECISION['bases']))
            self.assertEqual(route, '/v1/systemone')
            payload = json.loads(data)
            self.assertEqual(set(payload['questions']), {'confidence', 'reasoning', 'engagement'})
            self.assertIn(transcript, payload['state'])
            for excluded in ('referenceAnswer', 'referenceSolution', 'correctness', 'EDITED_WORK'):
                self.assertNotIn(excluded, payload['state'])
            return systemone_reply(payload)
        with patch('model_connections.request', side_effect=reply) as local:
            code, value = self.request('/api/learning-signals', {
                'questionId': QUESTION['ID'], 'transcript': transcript,
                'answer': '4', 'thoughts': 'EDITED_WORK'})
        self.assertEqual(code, 200)
        self.assertEqual(value['source'], 'original_speech')
        self.assertEqual(value['transcript'], transcript)
        self.assertEqual(len(value['signals']), 3)
        self.assertTrue(value['decisionConfigured'])
        local.assert_called_once()
        self.server.openai.infer.assert_not_called()
        self.server.chatgpt.infer.assert_not_called()

    def test_correct_answer_with_thinking_remains_unresolved_until_math_tutor(self):
        self.configure()
        with patch('model_connections.request', side_effect=AssertionError('Mathematics must not call d3-mini')) as local:
            code, value = self.request('/api/assessment', ATTEMPT)
        self.assertEqual(code, 200)
        self.assertEqual(value['answerCategory'], 'correct')
        self.assertTrue(value['answerCorrect'])
        self.assertEqual(value['category'], 'cannot_judge')
        self.assertFalse(value['modelUsed'])
        self.assertEqual(value['decisionRequests'], 0)
        self.assertTrue(value['decisionConfigured'])
        self.assertTrue(value['inferenceConfigured'])
        self.assertTrue(self.server.assessor.config.configured)
        self.assertEqual(self.server.assessor.config.model, 'd3-mini')
        local.assert_not_called()
        self.server.openai.infer.assert_not_called()
        self.server.chatgpt.infer.assert_not_called()

    def test_codex_tutor_receives_edited_work_and_no_original_speech(self):
        self.configure()
        edited = 'I counted two pairs and added 2+2=4.'
        original = 'ORIGINAL_SPEECH_WITH_RECOGNITION_ERROR'
        turn = {'revisionId': 'edited-current', 'action': 'submit', 'assistance': 'none', 'previous': None}
        attempt = {**ATTEMPT, 'bank': 'cn-math', 'thoughts': edited, 'turn': turn,
                   'originalSpeech': {'transcript': original, 'audio': 'PRIVATE_AUDIO'},
                   'transcript': original, 'notebook': ['PRIVATE_NOTEBOOK']}
        with patch('model_connections.request', side_effect=AssertionError('No local mathematical request')) as local, \
             patch('serve_math_practice.transcribe', side_effect=AssertionError('Do not transcribe submitted text')) as speech:
            code, checked = self.request('/api/assessment', attempt)
            self.assertEqual(code, 200)
            self.assertEqual(checked['category'], 'cannot_judge')
            code, value = self.request('/api/tutor', {
                **attempt, 'category': checked['category'], 'answerCategory': checked['answerCategory']})
        self.assertEqual(code, 200)
        self.assertEqual(value['category'], 'correct')
        self.assertEqual(value['answerCategory'], 'correct')
        self.assertEqual(value['revisionId'], turn['revisionId'])
        self.assertTrue(value['decisionConfigured'])
        self.server.openai.infer.assert_called_once()
        call = self.server.openai.infer.call_args
        self.assertEqual(call.args[0], CODEX)
        prompt = json.loads(call.args[1])
        self.assertEqual(prompt['studentSubmission'], {'answer': '4', 'reasoning': edited})
        self.assertEqual(prompt['turn'], turn)
        for excluded in (original, 'PRIVATE_AUDIO', 'PRIVATE_NOTEBOOK', 'qwen3-asr', 'd3-mini'):
            self.assertNotIn(excluded, json.dumps(prompt))
        self.assertEqual(call.args[4], [])
        local.assert_not_called()
        speech.assert_not_called()
        self.server.chatgpt.infer.assert_not_called()

    def test_answer_only_submission_gets_one_combined_tutor_review(self):
        self.configure()
        for answer, expected in (('4', 'correct'), ('5', 'wrong')):
            with self.subTest(answer=answer):
                self.server.openai.infer.reset_mock()
                self.server.openai.infer.return_value = json.dumps({
                    'category': 'correct', 'answerCategory': expected,
                    'coach': 'You added both pairs correctly.', 'hint': 'An unsupported hint.'})
                attempt = {**ATTEMPT, 'answer': answer, 'thoughts': '   '}
                with patch('model_connections.request', side_effect=AssertionError('No separate mathematical inference')) as local:
                    code, checked = self.request('/api/assessment', attempt)
                    self.assertEqual(code, 200)
                    self.assertEqual(checked['category'], 'cannot_judge')
                    self.assertFalse(checked['modelUsed'])
                    code, review = self.request('/api/tutor', {
                        **attempt, 'category': checked['category'],
                        'answerCategory': checked['answerCategory']})
                self.assertEqual(code, 200)
                self.assertEqual(review['category'], 'partial')
                self.assertEqual(review['answerCategory'], expected)
                self.assertNotIn('You added', review['coach'])
                self.assertTrue(review['coach'])
                self.assertEqual(review['hint'], '')
                self.server.openai.infer.assert_called_once()
                prompt = json.loads(self.server.openai.infer.call_args.args[1])
                self.assertEqual(prompt['studentSubmission'], {'answer': answer, 'reasoning': ''})
                self.assertEqual(prompt['reference']['solutionAvailability'], 'present')
                local.assert_not_called()

    def test_speech_input_uses_qwen_asr_without_any_math_or_signal_call(self):
        self.configure()
        wav = io.BytesIO()
        with wave.open(wav, 'wb') as recording:
            recording.setnchannels(1)
            recording.setsampwidth(2)
            recording.setframerate(16000)
            recording.writeframes(b'\0\0' * 1600)
        def reply(config, route, data, content_type, timeout=None):
            self.assertEqual(config.model, 'qwen3-asr')
            self.assertEqual(config.bases, tuple(LOCAL_SPEECH['bases']))
            self.assertEqual(route, '/v1/audio/transcriptions')
            self.assertIn('multipart/form-data', content_type)
            self.assertIn(b'qwen3-asr', data)
            self.assertIn(b'RIFF', data)
            return {'text': 'Original recognized thinking.'}
        with patch('model_connections.request', side_effect=reply) as local:
            code, value = self.request('/api/transcription', audio=wav.getvalue())
        self.assertEqual(code, 200)
        self.assertEqual(value['text'], 'Original recognized thinking.')
        self.assertEqual(value['model'], 'qwen3-asr')
        local.assert_called_once()
        self.server.openai.infer.assert_not_called()
        self.server.chatgpt.infer.assert_not_called()

    def test_legacy_default_still_uses_decision_model_for_mathematics(self):
        self.configure(inference_math=False)
        self.assertEqual(self.settings.math_assessment_provider(), 'decision')
        with patch('model_connections.request', side_effect=lambda config, route, data, *args, **kwargs:
                   systemone_reply(json.loads(data))) as local:
            code, value = self.request('/api/assessment', ATTEMPT)
        self.assertEqual(code, 200)
        self.assertEqual(value['category'], 'correct')
        self.assertTrue(value['modelUsed'])
        self.assertEqual(value['decisionRequests'], 2)
        self.assertTrue(value['decisionConfigured'])
        self.assertEqual([call.args[0].model for call in local.call_args_list], ['d3-mini', 'd3-mini'])
        self.assertEqual([set(json.loads(call.args[2])['questions']) for call in local.call_args_list],
                         [{'correctness'}, {'answer_correctness'}])
        self.server.openai.infer.assert_not_called()

    def test_engine_and_status_keep_selected_settings_and_signal_connection(self):
        self.configure()
        with patch('model_connections.request', return_value={'data': [{'id': 'd3-mini'}]}) as local:
            self.assertEqual(self.request('/api/assessment', ATTEMPT)[0], 200)
            code, engine = self.request('/api/engine')
            self.assertEqual(code, 200)
            self.assertEqual(engine['settingsInstance'], engine_instance(self.settings.path))
            self.assertNotEqual(engine['settingsInstance'], engine_instance(self.root / 'another-setting.yaml'))
            code, status = self.request('/api/status/decision')
        self.assertEqual(code, 200)
        self.assertTrue(status['configured'])
        self.assertTrue(status['ready'])
        local.assert_called_once()
        self.assertEqual(local.call_args.args[0].model, 'd3-mini')
        self.assertEqual(local.call_args.args[1], '/v1/models')
        self.server.openai.infer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
