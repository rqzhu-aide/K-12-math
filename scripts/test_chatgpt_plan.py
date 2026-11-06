"""Official plan transport checks using temporary credentials and mocked OpenAI.

No real account login, existing credential store, or live inference is used.
"""
import base64
import hashlib
from http.client import IncompleteRead
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse
import urllib.request

from chatgpt_plan import (AUTHORIZE, CALLBACK_PATH, ChatGPTPlan, DIRECT_SCOPE,
                          DISCOVERY, ISSUER, PlanError, RESOURCE, SCOPES, TOKEN,
                          _dependency_available)


CLIENT = 'oaiapp_math_practice_test'
SELECTION = {'model': 'test-model', 'effort': 'medium'}
REVIEW = '{"category":"correct","answerCategory":"correct","coach":"Your explanation is correct.","hint":""}'
DISCOVERY_DATA = {'issuer': ISSUER, 'authorization_endpoint': AUTHORIZE, 'token_endpoint': TOKEN,
                  'jwks_uri': ISSUER + '/.well-known/jwks.json',
                  'revocation_endpoint': ISSUER + '/api/accounts/oauth/revoke'}


class EventStream(io.BytesIO):
    headers = {'Content-Type': 'text/event-stream'}


def stream(*events):
    return EventStream(''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode('utf-8'))


class PlanFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary.name) / 'account'
        self.plan = ChatGPTPlan(self.home)
        self.dependency = patch('chatgpt_plan._dependency_available', return_value=True)
        self.dependency.start()
        self.browser = patch('chatgpt_plan.webbrowser.open', return_value=True)
        self.open_browser = self.browser.start()

    def tearDown(self):
        self.plan.close()
        self.dependency.stop()
        self.browser.stop()
        self.temporary.cleanup()

    def account(self, **changes):
        return {'client_id': CLIENT, 'issuer': ISSUER, 'subject': 'subject-one',
                'email': 'learner@example.test', 'name': 'Test learner',
                'access_token': 'mock-access', 'refresh_token': 'mock-refresh', 'id_token': 'mock-id',
                'scopes': SCOPES.split(), 'expires_at': time.time() + 3600, **changes}

    def save(self, account=None):
        with self.plan._storage():
            self.plan._write({'host_id': 'urn:uuid:eea5803c-a988-4133-b983-95a0c90fae1a',
                              'account': account if account is not None else self.account()})

    def token_response(self, **changes):
        return {'access_token': 'new-access', 'refresh_token': 'new-refresh', 'id_token': 'new-id',
                'scope': SCOPES, 'token_type': 'Bearer', 'expires_in': 3600, **changes}

    def begin(self):
        self.plan.start_login()
        url = self.open_browser.call_args.args[0]
        values = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        return {key: value[0] for key, value in values.items()}

    def finish(self, query=None):
        attempt = self.plan._pending
        return self.plan._callback(urllib.parse.urlencode(query or {'state': attempt['state'],
                                  'code': 'test-code', 'client_id': CLIENT}))


class LoginTests(PlanFixture):
    def test_status_is_offline_and_does_not_create_storage_or_expose_tokens(self):
        with patch.object(self.plan, '_request', side_effect=AssertionError('No network')):
            status = self.plan.status()
        self.assertEqual(status['state'], 'signed_out')
        self.assertFalse(self.home.exists())
        self.save()
        text = json.dumps(self.plan.status())
        for secret in ('mock-access', 'mock-refresh', 'mock-id'):
            self.assertNotIn(secret, text)
        self.assertIsNone(self.plan.status()['loginUrl'])

    def test_missing_shared_dependency_is_actionable(self):
        with patch('chatgpt_plan._dependency_available', return_value=False):
            self.assertEqual(self.plan.status()['state'], 'unavailable')
            self.assertIn('pip install --user', self.plan.status()['message'])
            with self.assertRaisesRegex(PlanError, 'PyJWT'):
                self.plan.start_login()
        self.open_browser.assert_not_called()

    def test_registration_uses_new_pkce_and_persisted_host_id(self):
        first = self.begin()
        attempt = self.plan._pending
        self.assertEqual(first['client_id'], 'dynamic_agent_client')
        self.assertEqual(first['agent_name_hint'], 'Math Practice')
        self.assertTrue(first['ext_agent_host_id'].startswith('urn:uuid:'))
        self.assertEqual(first['scope'], SCOPES)
        self.assertEqual(first['resource'], RESOURCE)
        self.assertTrue(first['redirect_uri'].startswith('http://127.0.0.1:'))
        self.assertTrue(first['redirect_uri'].endswith(CALLBACK_PATH))
        expected = base64.urlsafe_b64encode(hashlib.sha256(attempt['verifier'].encode('ascii')).digest()).rstrip(b'=').decode('ascii')
        self.assertEqual(first['code_challenge'], expected)
        self.plan.cancel_login()
        second = self.begin()
        self.assertEqual(second['ext_agent_host_id'], first['ext_agent_host_id'])
        self.assertNotEqual(second['state'], first['state'])
        self.assertNotEqual(second['nonce'], first['nonce'])
        self.assertNotEqual(second['code_challenge'], first['code_challenge'])

    def test_successful_registration_stores_verified_identity_then_discovers_models(self):
        values = self.begin()
        claims = {'sub': 'subject-one', 'iss': ISSUER, 'email': 'learner@example.test'}
        with patch.object(self.plan, '_validate_identity', return_value=claims) as verify, \
                patch.object(self.plan, '_request', side_effect=[self.token_response(),
                    {'models': [{'slug': 'second', 'display_name': 'Second', 'visibility': 'list'},
                                {'slug': 'hidden', 'visibility': 'hide'},
                                {'slug': 'first', 'display_name': 'First', 'visibility': 'list'}]}]) as request:
            result, _ = self.finish()
        self.assertEqual(result, 200)
        self.assertIsNone(self.plan._pending)
        verify.assert_called_once_with('new-id', CLIENT, values['nonce'], None)
        form = request.call_args_list[0].kwargs['form']
        self.assertEqual(form['client_id'], CLIENT)
        self.assertEqual(form['redirect_uri'], values['redirect_uri'])
        self.assertEqual(form['resource'], RESOURCE)
        self.assertNotIn('client_secret', form)
        self.assertEqual(request.call_args_list[1].args[0], RESOURCE + '/models')
        status = self.plan.status()
        self.assertTrue(status['canTest'])
        self.assertEqual(status['account']['label'], 'learner@example.test')
        self.assertEqual([model['model'] for model in status['modelSuggestions']], ['second', 'first'])
        self.assertEqual(self.plan._read()['account']['access_token'], 'new-access')
        restarted = ChatGPTPlan(self.home)
        with patch.object(restarted, '_request', side_effect=AssertionError('No network on status')):
            self.assertEqual(restarted.status()['modelSuggestions'], status['modelSuggestions'])
        restarted.close()

    def test_missing_scope_retains_identity_without_inference_or_model_discovery(self):
        self.begin()
        with patch.object(self.plan, '_validate_identity', return_value={'sub': 'subject-one', 'iss': ISSUER}), \
                patch.object(self.plan, '_request', return_value={'id_token': 'new-id', 'scope': 'openid email profile'}) as request:
            self.assertEqual(self.finish()[0], 200)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(self.plan.status()['state'], 'signed_in')
        self.assertFalse(self.plan.status()['planEnabled'])
        with self.assertRaisesRegex(PlanError, 'permission'):
            self.plan.infer(SELECTION, 'prompt', 'instructions', {})
        values = self.begin()
        self.assertEqual(values['prompt'], 'consent')

    def test_unverified_denied_repeated_and_expired_callbacks_never_exchange(self):
        self.begin()
        with patch.object(self.plan, '_request') as request:
            self.assertEqual(self.finish({'state': 'wrong', 'code': 'test-code', 'client_id': CLIENT})[0], 400)
            self.assertEqual(self.plan._callback('state=a&state=b&code=code')[0], 400)
            self.assertEqual(self.finish({'state': self.plan._pending['state'], 'error': 'access_denied'})[0], 400)
            self.assertIsNone(self.plan._pending)
            request.assert_not_called()
        self.begin()
        self.plan._pending['expires_at'] = time.monotonic() - 1
        with patch.object(self.plan, '_request') as request:
            self.assertEqual(self.finish()[0], 400)
            request.assert_not_called()

    def test_cancel_during_code_exchange_does_not_install_credentials(self):
        self.begin()
        entered, release = threading.Event(), threading.Event()
        def exchange(*args, **kwargs):
            entered.set()
            release.wait(3)
            return self.token_response()
        with patch.object(self.plan, '_request', side_effect=exchange), \
                patch.object(self.plan, '_validate_identity', return_value={'sub': 'subject-one', 'iss': ISSUER}):
            worker = threading.Thread(target=self.finish)
            worker.start()
            self.assertTrue(entered.wait(3))
            self.plan.cancel_login()
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertIsNone(self.plan._read()['account'])
        self.assertEqual(self.plan.status()['state'], 'signed_out')
        self.assertFalse(self.plan.status()['planEnabled'])

    def test_reauthorization_retains_client_and_hints_without_frontend_url(self):
        self.save()
        values = self.begin()
        self.assertEqual(values['client_id'], CLIENT)
        self.assertEqual(values['id_token_hint'], 'mock-id')
        self.assertNotIn('agent_name_hint', values)
        self.assertIsNone(self.plan.status()['loginUrl'])
        with patch.object(self.plan, '_request') as request:
            self.assertEqual(self.finish({'state': values['state'], 'code': 'code', 'client_id': 'oaiapp_other'})[0], 400)
            request.assert_not_called()
        self.assertEqual(self.plan._read()['account']['access_token'], 'mock-access')

    def test_invalid_grant_retry_keeps_issued_registration_id(self):
        self.begin()
        with patch.object(self.plan, '_request', side_effect=PlanError('Expired code', 400, code='invalid_grant')):
            self.assertEqual(self.finish()[0], 400)
        self.assertEqual(self.begin()['client_id'], CLIENT)

    def test_explicit_new_account_can_replace_expired_account_without_premature_overwrite(self):
        self.save(self.account(expires_at=0, refresh_token=None))
        self.plan.start_login(new_account=True)
        values = urllib.parse.parse_qs(urllib.parse.urlsplit(self.open_browser.call_args.args[0]).query)
        self.assertEqual(values['client_id'], ['dynamic_agent_client'])
        self.assertNotIn('id_token_hint', values)
        self.assertEqual(self.plan._read()['account']['subject'], 'subject-one')
        self.plan.cancel_login()
        self.assertEqual(self.plan._read()['account']['subject'], 'subject-one')

    def test_saved_registration_selection_rejects_unrecognized_or_forged_ids(self):
        for value in ('oaiapp_forged', {'client_id': CLIENT}):
            with self.assertRaises(PlanError):
                self.plan.start_login(client_id=value)
        self.open_browser.assert_not_called()

    def test_callback_listener_rejects_wrong_host_and_path_without_credentials(self):
        values = self.begin()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        bad = urllib.request.Request(values['redirect_uri'] + '?state=invalid', headers={'Host': 'attacker.example'})
        with self.assertRaises(urllib.error.HTTPError) as error:
            opener.open(bad, timeout=2)
        self.assertEqual(error.exception.code, 400)
        error.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as error:
            opener.open(values['redirect_uri'].replace(CALLBACK_PATH, '/wrong'), timeout=2)
        self.assertEqual(error.exception.code, 404)
        error.exception.close()

    def test_windows_store_does_not_contain_tokens_and_restart_preserves_connection(self):
        self.save()
        raw = (self.home / 'account.dat').read_bytes()
        if os.name == 'nt':
            self.assertNotIn(b'mock-access', raw)
            self.assertNotIn(b'mock-refresh', raw)
        else:
            self.assertEqual((self.home / 'account.dat').stat().st_mode & 0o077, 0)
        restarted = ChatGPTPlan(self.home)
        self.assertTrue(restarted.status()['canTest'])
        restarted.close()


class RefreshAndInferenceTests(PlanFixture):
    def test_valid_access_token_without_refresh_is_usable_until_expiry(self):
        self.save(self.account(expires_at=time.time() + 30, refresh_token=None))
        self.assertTrue(self.plan.status()['canTest'])
        with patch.object(self.plan, '_request') as request:
            self.assertEqual(self.plan._access()['access_token'], 'mock-access')
        request.assert_not_called()

    def test_refresh_that_removes_plan_permission_does_not_send_inference(self):
        self.save(self.account(expires_at=0))
        result = self.token_response(id_token=None, scope='openid email profile')
        with patch.object(self.plan, '_request', return_value=result) as request:
            with self.assertRaisesRegex(PlanError, 'permission'):
                self.plan.infer(SELECTION, 'prompt', 'instructions', None)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(self.plan.status()['state'], 'signed_in')
        self.assertFalse(self.plan.status()['planEnabled'])

    def test_another_process_switching_accounts_replaces_the_model_catalog(self):
        self.save()
        with patch.object(self.plan, '_request', return_value={'models': [
                {'slug': 'first-account-model', 'visibility': 'list'}]}):
            self.plan.refresh_models()
        other = ChatGPTPlan(self.home)
        with other._storage():
            record = other._read()
            record['account'] = self.account(client_id='oaiapp_second', subject='subject-two')
            record['model_suggestions'] = [{'model': 'second-account-model', 'label': 'Second'}]
            other._write(record)
        self.assertEqual(self.plan.status()['modelSuggestions'], record['model_suggestions'])
        other.close()

    def test_malformed_completed_message_content_is_a_safe_provider_error(self):
        self.save()
        response = stream({'type': 'response.completed', 'response': {'status': 'completed',
                          'output': [{'type': 'message', 'content': 1}]}})
        response.headers = {'x-request-id': 'req-malformed'}
        with patch.object(self.plan, '_request', return_value=response):
            with self.assertRaisesRegex(PlanError, 'unreadable completed response') as caught:
                self.plan.infer(SELECTION, 'prompt', 'instructions', None)
        self.assertEqual(caught.exception.request_id, 'req-malformed')

    def test_interrupted_nonstream_response_is_a_safe_provider_error(self):
        class Interrupted(EventStream):
            def read(self, *args):
                raise IncompleteRead(b'partial')
        with patch.object(self.plan._opener, 'open', return_value=Interrupted()):
            with self.assertRaises(PlanError):
                self.plan._request(RESOURCE + '/models', token='mock-access')

    def test_interrupted_error_body_retains_the_http_status_and_request_id(self):
        class Interrupted(EventStream):
            def read(self, *args):
                raise IncompleteRead(b'partial')
        response = urllib.error.HTTPError(RESOURCE + '/models', 503, 'Unavailable',
                                         {'x-request-id': 'req-truncated'}, Interrupted())
        with patch.object(self.plan._opener, 'open', side_effect=response):
            with self.assertRaises(PlanError) as caught:
                self.plan._request(RESOURCE + '/models', token='mock-access')
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(caught.exception.request_id, 'req-truncated')

    def test_malformed_refresh_does_not_overwrite_a_working_account(self):
        self.save(self.account(expires_at=0))
        for changes in ({'expires_in': None}, {'token_type': None}, {'access_token': None},
                        {'refresh_token': []}, {'scope': []}):
            with self.subTest(changes=changes), patch.object(self.plan, '_request', return_value=self.token_response(**changes)):
                with self.assertRaises(PlanError):
                    self.plan._access()
            self.assertEqual(self.plan._read()['account']['refresh_token'], 'mock-refresh')

    def test_two_instances_serialize_rotating_refresh_for_the_same_account(self):
        self.save(self.account(expires_at=0))
        other = ChatGPTPlan(self.home)
        count, results = [], []
        def exchange(*args, **kwargs):
            count.append(1)
            time.sleep(0.1)
            return self.token_response(id_token=None)
        def access(plan):
            try:
                results.append(plan._access()['access_token'])
            except Exception as error:
                results.append(error)
        with patch.object(self.plan, '_request', side_effect=exchange), patch.object(other, '_request', side_effect=exchange):
            first = threading.Thread(target=access, args=(self.plan,))
            second = threading.Thread(target=access, args=(other,))
            first.start()
            second.start()
            first.join(3)
            second.join(3)
        self.assertEqual(count, [1])
        self.assertEqual(results, ['new-access', 'new-access'])
        other.close()

    def test_refresh_uses_issued_id_replaces_rotating_tokens_and_retains_identity(self):
        self.save(self.account(expires_at=0))
        with patch.object(self.plan, '_request', return_value=self.token_response(id_token=None)) as request:
            account = self.plan._access()
        form = request.call_args.kwargs['form']
        self.assertEqual(form, {'grant_type': 'refresh_token', 'client_id': CLIENT,
                                'refresh_token': 'mock-refresh', 'resource': RESOURCE})
        self.assertEqual(account['access_token'], 'new-access')
        self.assertEqual(account['refresh_token'], 'new-refresh')
        self.assertEqual(account['id_token'], 'mock-id')
        self.assertEqual(account['subject'], 'subject-one')
        self.assertEqual(self.plan._read()['account']['refresh_token'], 'new-refresh')

    def test_terminal_refresh_clears_only_tokens_and_temporary_failure_keeps_them(self):
        self.save(self.account(expires_at=0))
        with patch.object(self.plan, '_request', side_effect=PlanError('Temporary', 503)):
            with self.assertRaises(PlanError):
                self.plan._access()
        self.assertEqual(self.plan._read()['account']['refresh_token'], 'mock-refresh')
        with patch.object(self.plan, '_request', side_effect=PlanError('Expired', 400, code='invalid_grant')):
            with self.assertRaisesRegex(PlanError, 'connection ended'):
                self.plan._access()
        account = self.plan._read()['account']
        self.assertNotIn('refresh_token', account)
        self.assertEqual(account['client_id'], CLIENT)
        self.assertEqual(account['subject'], 'subject-one')
        self.assertEqual(self.plan.status()['state'], 'signed_out')
        self.assertFalse(self.plan.status()['planEnabled'])
        self.assertIn('sign in again', self.plan.status()['message'])

    def test_streaming_inference_uses_public_route_without_unsupported_parameters(self):
        self.save()
        response = stream({'type': 'response.output_text.delta', 'delta': REVIEW},
                          {'type': 'response.completed', 'response': {'status': 'completed'}})
        with patch.object(self.plan, '_request', return_value=response) as request:
            self.assertEqual(self.plan.infer(SELECTION, 'student prompt', 'tutor instructions', {'type': 'object'},
                                            images=('data:image/png;base64,abc',)), REVIEW)
        self.assertEqual(request.call_args.args[0], RESOURCE + '/responses')
        self.assertEqual(request.call_args.kwargs['token'], 'mock-access')
        body = request.call_args.kwargs['body']
        self.assertEqual(body['instructions'], 'tutor instructions')
        self.assertEqual(body['input'][0]['content'][1]['type'], 'input_image')
        self.assertFalse(body['store'])
        self.assertTrue(body['stream'])
        self.assertEqual(body['text']['format']['type'], 'json_schema')
        self.assertEqual(body['reasoning'], {'effort': 'medium'})
        self.assertEqual(set(body), {'model', 'instructions', 'input', 'store', 'stream', 'text', 'reasoning'})

    def test_selected_extra_high_effort_is_transmitted(self):
        self.save()
        response = stream({'type': 'response.output_text.delta', 'delta': REVIEW},
                          {'type': 'response.completed', 'response': {'status': 'completed'}})
        with patch.object(self.plan, '_request', return_value=response) as request:
            self.plan.infer({**SELECTION, 'effort': 'xhigh'}, 'prompt', 'instructions', None)
        self.assertEqual(request.call_args.kwargs['body']['reasoning'], {'effort': 'xhigh'})

    def test_plan_stream_without_content_type_still_requires_a_completed_review(self):
        self.save(self.account())
        completed = {'type': 'response.completed', 'response': {'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': REVIEW}]}]}}
        wire = b'event: response.completed\ndata: ' + json.dumps(completed).encode() + b'\n\n'
        response = io.BytesIO(wire)
        response.headers = {'Transfer-Encoding': 'chunked'}
        with patch.object(self.plan, '_request', return_value=response):
            self.assertEqual(self.plan.infer(SELECTION, 'prompt', 'instructions', None), REVIEW)

        partial = stream({'type': 'response.output_text.delta', 'delta': REVIEW})
        partial.headers = {}
        with patch.object(self.plan, '_request', return_value=partial):
            with self.assertRaisesRegex(PlanError, 'before response.completed'):
                self.plan.infer(SELECTION, 'prompt', 'instructions', None)

        invalid = io.BytesIO(b'<html>Bad gateway</html>')
        invalid.headers = {'Content-Type': 'text/html'}
        with patch.object(self.plan, '_request', return_value=invalid):
            with self.assertRaisesRegex(PlanError, 'required streaming response'):
                self.plan.infer(SELECTION, 'prompt', 'instructions', None)

    def test_stream_requires_completed_event_and_rejects_failures_or_empty_output(self):
        self.save()
        for response, message in [
            (stream({'type': 'response.output_text.delta', 'delta': REVIEW}), 'before response.completed'),
            (stream({'type': 'response.failed', 'response': {'error': {'code': 'test_failure'}}}), 'could not complete'),
            (stream({'type': 'response.incomplete'}), 'did not complete'),
            (stream({'type': 'response.completed', 'response': {'status': 'completed'}}), 'without a text'),
            (EventStream(b'data: not JSON\n\n'), 'unreadable')]:
            with self.subTest(message=message), patch.object(self.plan, '_request', return_value=response):
                with self.assertRaisesRegex(PlanError, message):
                    self.plan.infer(SELECTION, 'prompt', 'instructions', None)

    def test_overloaded_service_does_not_suggest_an_account_permission_problem(self):
        body = {'error': {'type': 'service_unavailable_error', 'code': 'server_is_overloaded',
                          'message': 'Our servers are currently overloaded. Please try again later.',
                          'headers': {'retry-after': '303'}}}
        error = self.plan._provider_error(502, body, 'req-busy')
        self.assertEqual(str(error), "OpenAI's model service is busy. Try again later.")
        self.assertEqual(error.code, 'server_is_overloaded')
        self.assertEqual(error.request_id, 'req-busy')
        self.assertEqual(error.body, body)

    def test_unauthorized_and_usage_limit_do_not_fallback_or_erase_credentials(self):
        self.save()
        for status, code in [(401, 'subscription_sharing_invalid_user'),
                             (429, 'subscription_sharing_usage_limit_exceeded'),
                             (403, 'subscription_sharing_user_not_eligible')]:
            error = self.plan._provider_error(status, {'error': {'code': code, 'param': 'model'}}, 'req-test')
            with patch.object(self.plan, '_request', side_effect=error) as request:
                with self.assertRaises(PlanError) as caught:
                    self.plan.infer(SELECTION, 'prompt', 'instructions', None)
            self.assertEqual(caught.exception.status, status)
            self.assertEqual(caught.exception.code, code)
            self.assertEqual(caught.exception.request_id, 'req-test')
            self.assertEqual(request.call_count, 1)
            self.assertEqual(self.plan._read()['account']['access_token'], 'mock-access')

    def test_top_level_stream_error_retains_code_param_usage_guidance_and_request_id(self):
        self.save()
        response = stream({'type': 'error', 'code': 'subscription_sharing_usage_limit_exceeded',
                           'param': 'model', 'message': 'Provider diagnostic'})
        response.headers = {'Content-Type': 'text/event-stream', 'x-request-id': 'req-sse'}
        with patch.object(self.plan, '_request', return_value=response):
            with self.assertRaises(PlanError) as caught:
                self.plan.infer(SELECTION, 'prompt', 'instructions', None)
        self.assertEqual(caught.exception.code, 'subscription_sharing_usage_limit_exceeded')
        self.assertEqual(caught.exception.param, 'model')
        self.assertEqual(caught.exception.request_id, 'req-sse')
        self.assertIn('ChatGPT Settings > Usage', str(caught.exception))

    def test_interrupted_stream_and_invalid_utf8_become_safe_errors(self):
        self.save()
        class Interrupted(EventStream):
            def __iter__(self):
                raise IncompleteRead(b'partial')
        for response in (EventStream(b'data: \xff\n\n'), Interrupted()):
            response.headers = {'Content-Type': 'text/event-stream', 'x-request-id': 'req-interrupted'}
            with patch.object(self.plan, '_request', return_value=response):
                with self.assertRaisesRegex(PlanError, 'response was interrupted') as caught:
                    self.plan.infer(SELECTION, 'prompt', 'instructions', None)
            self.assertEqual(caught.exception.request_id, 'req-interrupted')

    def test_plain_detail_error_preserves_body_shape_and_request_id(self):
        response = urllib.error.HTTPError(RESOURCE + '/models', 503, 'Unavailable',
                                         {'x-request-id': 'request-one'}, io.BytesIO(b'{"detail":"routing unavailable"}'))
        with patch.object(self.plan._opener, 'open', side_effect=response):
            with self.assertRaises(PlanError) as caught:
                self.plan._request(RESOURCE + '/models', token='mock-access')
        self.assertEqual(caught.exception.body, {'detail': 'routing unavailable'})
        self.assertEqual(caught.exception.request_id, 'request-one')

    def test_sign_out_revokes_refresh_and_keeps_registration_for_reauthorization(self):
        self.save()
        self.plan._discovery = DISCOVERY_DATA
        with patch.object(self.plan, '_request', return_value={}) as request:
            status = self.plan.sign_out()
        self.assertEqual(request.call_args.args[0], DISCOVERY_DATA['revocation_endpoint'])
        self.assertEqual(request.call_args.kwargs['form']['token_type_hint'], 'refresh_token')
        self.assertEqual(status['state'], 'signed_out')
        self.assertFalse(status['canTest'])
        record = self.plan._read()
        self.assertIsNone(record['account'])
        self.assertEqual(record['registrations'][CLIENT]['client_id'], CLIENT)
        self.assertNotIn('id_token', record['registrations'][CLIENT])
        self.assertEqual(status['registrations'], [{'id': CLIENT, 'label': 'learner@example.test'}])
        self.assertEqual(self.begin()['client_id'], 'dynamic_agent_client')
        self.plan.cancel_login()
        self.plan.start_login(client_id=CLIENT)
        values = urllib.parse.parse_qs(urllib.parse.urlsplit(self.open_browser.call_args.args[0]).query)
        self.assertEqual(values['client_id'], [CLIENT])
        self.assertNotIn('id_token_hint', values)

    def test_sign_out_clears_locally_and_reports_unconfirmed_remote_revocation(self):
        self.save()
        with patch.object(self.plan, '_request', side_effect=PlanError('Network', 503)):
            status = self.plan.sign_out()
        self.assertIn('Remote revocation was not confirmed', status['message'])
        self.assertIsNone(self.plan._read()['account'])


@unittest.skipUnless(_dependency_available(), 'Install user-wide PyJWT[crypto] for signature tests')
class IdentityTests(PlanFixture):
    @classmethod
    def setUpClass(cls):
        import jwt
        from cryptography.hazmat.primitives.asymmetric import rsa
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwk.update(kid='math-practice-key', alg='RS256', use='sig')

    def signed(self, **changes):
        import jwt
        now = int(time.time())
        claims = {'iss': ISSUER, 'sub': 'subject-one', 'aud': [CLIENT], 'iat': now,
                  'exp': now + 3600, 'nonce': 'expected-nonce', **changes}
        return jwt.encode(claims, self.key, algorithm='RS256', headers={'kid': 'math-practice-key'})

    def test_signed_identity_verifies_with_official_discovery_and_jwks(self):
        with patch.object(self.plan, '_request', side_effect=[DISCOVERY_DATA, {'keys': [self.jwk]}]) as request:
            claims = self.plan._validate_identity(self.signed(), CLIENT, 'expected-nonce')
        self.assertEqual(claims['sub'], 'subject-one')
        self.assertEqual(request.call_args_list[0].args[0], DISCOVERY)
        self.assertEqual(request.call_args_list[1].args[0], DISCOVERY_DATA['jwks_uri'])

    def test_wrong_signature_issuer_audience_nonce_expiry_and_changed_account_are_rejected(self):
        import jwt
        self.plan._jwks, self.plan._jwks_saved = {'keys': [self.jwk]}, time.time()
        from cryptography.hazmat.primitives.asymmetric import rsa
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        bad_signature = jwt.encode({'iss': ISSUER, 'sub': 'subject-one', 'aud': CLIENT, 'iat': int(time.time()),
                                    'exp': int(time.time()) + 3600, 'nonce': 'expected-nonce'},
                                   other, algorithm='RS256', headers={'kid': 'math-practice-key'})
        cases = [bad_signature, self.signed(iss='https://attacker.example'), self.signed(aud=['oaiapp_other']),
                 self.signed(nonce='wrong'), self.signed(exp=int(time.time()) - 60), self.signed(sub='other-subject')]
        for encoded in cases:
            with self.subTest(encoded=encoded[:16]):
                with self.assertRaisesRegex(PlanError, 'identity could not be verified'):
                    self.plan._validate_identity(encoded, CLIENT, 'expected-nonce', self.account())

    def test_unfamiliar_key_refreshes_jwks_and_unsafe_discovery_is_rejected(self):
        self.plan._jwks, self.plan._jwks_saved = {'keys': []}, time.time()
        self.plan._discovery = DISCOVERY_DATA
        with patch.object(self.plan, '_request', return_value={'keys': [self.jwk]}) as request:
            self.plan._validate_identity(self.signed(), CLIENT, 'expected-nonce')
        request.assert_called_once_with(DISCOVERY_DATA['jwks_uri'])
        self.plan._discovery = None
        with patch.object(self.plan, '_request', return_value={**DISCOVERY_DATA, 'jwks_uri': 'https://attacker.example/keys'}):
            with self.assertRaisesRegex(PlanError, 'unexpected endpoint'):
                self.plan._openid()

    def test_malformed_discovery_and_jwks_are_safe_identity_errors(self):
        for value in (1, None, ['https://auth.openai.com/keys'], 'https://[invalid'):
            self.plan._discovery = None
            with self.subTest(endpoint=value), patch.object(self.plan, '_request', return_value={
                    **DISCOVERY_DATA, 'jwks_uri': value}):
                with self.assertRaises(PlanError):
                    self.plan._openid()
        for value in ([], {'keys': None}, {'keys': [None]}, {'keys': [1]}):
            self.plan._jwks, self.plan._jwks_saved = value, time.time()
            with self.subTest(jwks=value):
                with self.assertRaises(PlanError):
                    self.plan._validate_identity(self.signed(), CLIENT, 'expected-nonce')


if __name__ == '__main__':
    unittest.main()
