"""Exercise configured API connections against real loopback HTTP services only."""
from contextlib import contextmanager
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import wave

from connection_settings import ConnectionSettings
from model_connections import model_status, test_inference as check_inference, test_speech as check_speech, transcribe
from practice_tutor import review_submission
from serve_math_practice import Handler
from student_assessment import AssessmentError, ModelConfig, StudentAssessment


QUESTION = {'ID': 'cnm_p001_q1', 'Bank': 'cn-math', 'ResponseType': 'numeric',
            'Question': 'What is 2 + 2?', 'Choices': {}, 'Correct Answer': '4',
            'Solution': 'Add two and two to get four.'}
ATTEMPT = {'questionId': QUESTION['ID'], 'answer': '4', 'thoughts': 'I added two and two.',
           'category': 'cannot_judge', 'answerCategory': 'correct'}
REVIEW = {'category': 'correct', 'answerCategory': 'correct', 'coach': 'Your explanation is correct.', 'hint': ''}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def wav_audio(seconds=1):
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\0\0' * round(16000 * seconds))
    return output.getvalue()


class Provider:
    def __init__(self, respond=None):
        self.calls = []
        self.respond = respond or self.task_reply

    def task_reply(self, call):
        if call['method'] != 'POST':
            return 404, {'error': {'message': 'No such route'}}, {}
        if call['path'] == '/v1/audio/transcriptions':
            return 200, {'text': 'I added two and two.'}, {}
        if call['path'] == '/v1/systemone':
            questions = call['json']['questions']
            return 200, {'answers': {name: {'probabilities': {key: int(index == 0)
                         for index, key in enumerate(question['criteria'])}}
                         for name, question in questions.items()}}, {}
        if call['path'] == '/v1/chat/completions':
            system = call['json']['messages'][0]['content']
            if 'Rubrics:\n' in system:
                rubrics = json.loads(system.split('Rubrics:\n', 1)[1])
                result = {name: {'code': next(iter(rubric['choices'])),
                                'evidence': 'The submitted words support this observation.'}
                          for name, rubric in rubrics.items()}
            else:
                result = REVIEW
            return 200, {'choices': [{'message': {'content': json.dumps(result)}}]}, {}
        return 404, {'error': {'message': 'No such route'}}, {}

    def __enter__(self):
        provider = self

        class APIHandler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle_request(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                call = {'path': self.path, 'method': self.command, 'body': raw,
                        'authorization': self.headers.get('Authorization'),
                        'contentType': self.headers.get('Content-Type', '')}
                if raw and call['contentType'].startswith('application/json'):
                    call['json'] = json.loads(raw)
                provider.calls.append(call)
                status, body, headers = provider.respond(call)
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', headers.get('Content-Length', str(len(data))))
                for name, value in headers.items():
                    if name != 'Content-Length':
                        self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

            do_GET = handle_request
            do_POST = handle_request

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), APIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class SettingsTransportTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        questions = self.root / 'cn-math-bank/questions'
        questions.mkdir(parents=True)
        (questions / (QUESTION['ID'] + '.json')).write_text(json.dumps(QUESTION), encoding='utf-8')
        self.settings = ConnectionSettings(self.root / 'config.json', defaults=ModelConfig())

    def tearDown(self):
        self.temporary.cleanup()
        self.environment.stop()

    def configure(self, provider, suffix='/v1', protocol='chat'):
        value = {'bases': [provider.base + suffix], 'model': 'fixture-model', 'apiKey': 'fixture-secret'}
        self.settings.save({'decision': {**value, 'protocol': protocol}, 'speech': value,
                            'inference': {**value, 'provider': 'api'}})
        return StudentAssessment(self.settings.decision_config(), root=self.root)

    @contextmanager
    def runtime(self, assessor):
        class QuietHandler(Handler):
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        server.settings, server.assessor = self.settings, assessor
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}'
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def fetch(self, base, route, body=None, content_type='application/json'):
        data = json.dumps(body).encode() if body is not None and content_type == 'application/json' else body
        with OPENER.open(urllib.request.Request(base + route, data=data,
                         headers={'Content-Type': content_type}), timeout=5) as response:
            return json.load(response)

    def test_task_only_chat_provider_passes_settings_and_real_practice(self):
        for suffix in ('', '/v1'):
            with self.subTest(base_suffix=suffix), Provider() as provider:
                assessor = self.configure(provider, suffix)
                with self.runtime(assessor) as runtime:
                    self.assertTrue(self.fetch(runtime, '/api/settings/inference/test', {})['ready'])
                    self.assertTrue(self.fetch(runtime, '/api/settings/decision/test', {})['ready'])
                    self.assertTrue(self.fetch(runtime, '/api/settings/speech/test', {})['ready'])
                    signals = self.fetch(runtime, '/api/learning-signals',
                                         {'questionId': QUESTION['ID'], 'transcript': 'I am unsure.'})
                    self.assertEqual(len(signals['signals']), 3)
                    assessment = self.fetch(runtime, '/api/assessment', ATTEMPT)
                    self.assertTrue(assessment['modelUsed'])
                    self.assertEqual(assessment['decisionRequests'], 2)
                    self.assertEqual(assessment['answerJudgment']['code'], 'correct')
                    review = review_submission(assessor, self.settings, None, ATTEMPT)
                    self.assertEqual(review['category'], 'correct')
                    transcript = self.fetch(runtime, '/api/transcription', wav_audio(0.25), 'audio/wav')
                    self.assertEqual(transcript['text'], 'I added two and two.')
                self.assertTrue(all(call['authorization'] == 'Bearer fixture-secret' for call in provider.calls))
                self.assertTrue(all(call['method'] == 'POST' for call in provider.calls))
                self.assertNotIn('fixture-secret', json.dumps(assessment))

    def test_systemone_needs_no_models_route_and_uses_fallback_for_task(self):
        with Provider(lambda call: (503, {}, {})) as failed, Provider() as provider:
            assessor = self.configure(provider, protocol='systemone')
            self.settings.save({'decision': {'bases': [failed.base + '/v1', provider.base + '/v1'],
                                             'apiKey': 'fixture-secret'}})
            assessor = StudentAssessment(self.settings.decision_config(), root=self.root)
            self.assertTrue(self.settings.test_decision({})['ready'])
            self.assertEqual(len(assessor.learning_signals({'questionId': QUESTION['ID'],
                                                          'transcript': 'I am unsure.'})['signals']), 3)
            result = assessor.assess(ATTEMPT)
            self.assertTrue(result['modelUsed'])
            self.assertEqual(result['answerJudgment']['code'], 'correct')
            self.assertTrue(failed.calls)
            self.assertTrue(all(call['path'] == '/v1/systemone' for call in failed.calls + provider.calls))

    def test_decision_test_covers_the_typed_answer_contract(self):
        for protocol in ('chat', 'systemone'):
            with self.subTest(protocol=protocol), Provider() as provider:
                self.configure(provider, protocol=protocol)
                self.assertTrue(self.settings.test_decision({})['ready'])
                seen = []
                for call in provider.calls:
                    if protocol == 'chat':
                        system = call['json']['messages'][0]['content']
                        seen.extend(json.loads(system.split('Rubrics:\n', 1)[1]))
                    elif call['method'] == 'POST':
                        seen.extend(call['json']['questions'])
                self.assertEqual(set(seen), {'confidence', 'reasoning', 'engagement',
                                             'correctness', 'answer_correctness'})

    def test_status_distinguishes_model_list_from_task_test_and_missing_listing(self):
        with Provider() as provider:
            assessor = self.configure(provider)
            with self.runtime(assessor) as runtime:
                for role in ('decision', 'speech', 'inference'):
                    status = self.fetch(runtime, '/api/status/' + role)
                    self.assertTrue(status['configured'])
                    self.assertFalse(status['ready'])
                    self.assertEqual(status['label'], 'Not tested')
                self.assertEqual(self.fetch(runtime, '/api/status')['label'], 'Not tested')
        with Provider(lambda call: (200, {'data': [{'id': 'fixture-model'}]}, {})) as provider:
            self.configure(provider)
            status = model_status(self.settings.speech_config())
            self.assertTrue(status['ready'])
            self.assertEqual(status['label'], 'Model listed')

    def test_catalog_omission_or_denied_access_does_not_claim_task_unavailability(self):
        for catalog_status, catalog_body, detail in (
                (200, {'data': [{'id': 'canonical-model'}]}, 'did not list'),
                (401, {}, 'credentials'), (403, {}, 'credentials')):
            with self.subTest(catalog_status=catalog_status), Provider() as provider:
                provider.respond = lambda call: ((catalog_status, catalog_body, {})
                    if call['path'] == '/v1/models' else provider.task_reply(call))
                assessor = self.configure(provider)
                with self.runtime(assessor) as runtime:
                    for role in ('decision', 'speech', 'inference'):
                        status = self.fetch(runtime, '/api/status/' + role)
                        self.assertTrue(status['configured'])
                        self.assertFalse(status['ready'])
                        self.assertEqual(status['label'], 'Not tested')
                        self.assertIn(detail, status['message'])
                        self.assertNotIn('fixture-secret', status['message'])
                        result = self.fetch(runtime, '/api/settings/' + role + '/test', {})
                        self.assertTrue(result['ready'])
                    self.assertTrue(self.fetch(runtime, '/api/assessment', ATTEMPT)['modelUsed'])
                    self.assertEqual(self.fetch(runtime, '/api/status')['label'], 'Not tested')

    def test_silent_probe_and_runtime_chunks_send_valid_multipart_wav(self):
        with Provider() as provider:
            self.configure(provider)
            self.assertTrue(check_speech(self.settings.speech_config())['ready'])
            result = transcribe(self.settings.speech_config(), wav_audio(55))
            self.assertEqual(result['chunks'], 3)
            durations = []
            for call in provider.calls:
                message = BytesParser(policy=policy.default).parsebytes(
                    ('Content-Type: ' + call['contentType'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + call['body'])
                fields = {part.get_param('name', header='content-disposition'): part.get_payload(decode=True)
                          for part in message.iter_parts()}
                self.assertEqual(fields['model'], b'fixture-model')
                with wave.open(io.BytesIO(fields['file'])) as wav:
                    self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1, 2, 16000))
                    durations.append(wav.getnframes() / 16000)
            self.assertEqual(durations[0], 1)
            self.assertTrue(all(0 < duration <= 26 for duration in durations))
            self.assertEqual(sum(durations[1:]), 55)

    def test_fallback_uses_only_explicit_bases_and_configured_key(self):
        for status in (401, 403, 429, 500):
            with self.subTest(first_status=status), Provider(lambda call: (status, {}, {})) as failed, Provider() as provider:
                self.configure(provider)
                config = ModelConfig((failed.base + '/v1', provider.base + '/v1'), 'fixture-model', 'fixture-secret')
                self.assertTrue(check_inference(config)['ready'])
                self.assertEqual([call['authorization'] for call in failed.calls + provider.calls],
                                 ['Bearer fixture-secret', 'Bearer fixture-secret'])

    def test_invalid_json_uses_next_configured_base(self):
        with Provider(lambda call: (200, b'not JSON', {})) as failed, Provider() as provider:
            config = ModelConfig((failed.base, provider.base + '/v1'), 'fixture-model')
            self.assertTrue(check_inference(config)['ready'])
            self.assertEqual(len(failed.calls), 1)
            self.assertIsNone(provider.calls[0]['authorization'])

    def test_truncated_http_response_is_a_retryable_transport_failure(self):
        with Provider(lambda call: (200, b'{}', {'Content-Length': '50'})) as failed, Provider() as provider:
            config = ModelConfig((failed.base, provider.base), 'fixture-model')
            self.assertTrue(check_inference(config)['ready'])
            with self.assertRaises(AssessmentError) as raised:
                check_inference(ModelConfig((failed.base,), 'fixture-model'))
            self.assertEqual(raised.exception.status, 503)

    def test_http_errors_are_displayable_without_provider_body_or_key(self):
        for status, expected in ((401, 'credentials'), (403, 'credentials'), (429, 'quota'),
                                 (400, 'request format'), (404, 'request format'),
                                 (422, 'request format'), (500, 'could not complete')):
            with self.subTest(status=status), Provider(lambda call: (status, {'secret': 'fixture-secret'}, {})) as provider:
                self.configure(provider)
                with self.assertRaises(AssessmentError) as raised:
                    check_inference(self.settings.decision_config())
                self.assertIn(expected, str(raised.exception))
                self.assertNotIn('fixture-secret', str(raised.exception))

    def test_cross_origin_redirect_does_not_forward_key_or_student_payload(self):
        with Provider() as destination:
            with Provider(lambda call: (302, {}, {'Location': destination.base + '/v1/chat/completions'})) as source:
                config = ModelConfig((source.base + '/v1',), 'fixture-model', 'fixture-secret', 'chat')
                with self.assertRaises(AssessmentError):
                    check_inference(config)
                self.assertEqual(destination.calls, [])

    def test_redirected_model_listing_does_not_forward_credentials(self):
        with Provider() as destination:
            with Provider(lambda call: (302, {}, {'Location': destination.base + '/v1/models'})) as source:
                status = model_status(ModelConfig((source.base,), 'fixture-model', 'fixture-secret'))
                self.assertFalse(status['ready'])
                self.assertIn('final API address', status['message'])
                self.assertEqual(destination.calls, [])

    def test_malformed_task_responses_never_become_successful_checks(self):
        for body in (None, {}, {'choices': []}, {'choices': [{'message': {'content': 'not JSON'}}]}):
            with self.subTest(body=body), Provider(lambda call: (200, body, {})) as provider:
                self.configure(provider)
                for check, config in ((check_inference, self.settings.decision_config()),
                                      (check_speech, self.settings.speech_config())):
                    with self.assertRaises(AssessmentError):
                        check(config)
                with self.assertRaises(AssessmentError):
                    self.settings.test_decision({})

    def test_failed_decision_preserves_exact_answer_without_approving_reasoning(self):
        with Provider(lambda call: (200, {}, {})) as provider:
            assessor = self.configure(provider)
            result = assessor.assess(ATTEMPT)
            self.assertEqual(result['answerCategory'], 'correct')
            self.assertEqual(result['category'], 'cannot_judge')
            self.assertFalse(result['modelUsed'])
            self.assertTrue(result['decisionUnavailable'])

    def test_invalid_systemone_probabilities_are_rejected_without_crashing(self):
        for invalid in (True, float('nan'), float('inf'), -1, 10 ** 400):
            def respond(call):
                questions = call['json']['questions']
                return 200, {'answers': {name: {'probabilities': {key: invalid
                                    for key in question['criteria']}}
                                    for name, question in questions.items()}}, {}
            with self.subTest(probability=repr(invalid)), Provider(respond) as provider:
                assessor = self.configure(provider, protocol='systemone')
                with self.assertRaises(AssessmentError):
                    assessor.learning_signals({'questionId': QUESTION['ID'], 'transcript': 'I am unsure.'})
                result = assessor.assess(ATTEMPT)
                self.assertEqual(result['category'], 'cannot_judge')
                self.assertTrue(result['decisionUnavailable'])

    def test_missing_model_listing_does_not_hide_auth_or_other_transport_failures(self):
        with Provider() as no_listing, Provider(lambda call: (401, {}, {})) as unauthorized:
            status = model_status(ModelConfig((no_listing.base, unauthorized.base), 'fixture-model', 'fixture-secret'))
            self.assertFalse(status['ready'])
            self.assertEqual(status['label'], 'Not tested')
            self.assertIn('model-list check failed', status['message'])
            self.assertIn('credentials', status['message'])

    def test_failed_catalog_probe_preserves_the_cause_without_claiming_offline(self):
        for code, body, detail in ((429, {}, 'quota'), (500, {}, 'could not complete'),
                                   (200, b'not JSON', 'could not complete'),
                                   (200, {}, 'invalid model list')):
            with self.subTest(code=code, body=body), Provider(lambda call: (code, body, {})) as provider:
                status = model_status(ModelConfig((provider.base,), 'fixture-model', 'fixture-secret'))
                self.assertFalse(status['ready'])
                self.assertEqual(status['label'], 'Not tested')
                self.assertIn(detail, status['message'])
                self.assertNotIn('fixture-secret', status['message'])


if __name__ == '__main__':
    unittest.main()
