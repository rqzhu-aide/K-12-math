"""Saved Codex adapter checks with temporary files and a synthetic SDK only."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from openai_connection import OpenAIConnection
from student_assessment import AssessmentError


SELECTION = {'model': 'selected-model', 'effort': 'xhigh'}


class SavedCodexConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.connection = OpenAIConnection(self.root / 'work', home=self.root / 'codex')

    def tearDown(self):
        self.temporary.cleanup()

    def synthetic_sdk(self):
        thread = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
            status=SimpleNamespace(value='completed'), final_response='review text')))
        client = SimpleNamespace(thread_start=AsyncMock(return_value=thread), close=AsyncMock())
        sdk = SimpleNamespace(AsyncCodex=MagicMock(return_value=client),
                              CodexConfig=lambda **kwargs: SimpleNamespace(**kwargs),
                              Sandbox=SimpleNamespace(read_only='read-only'),
                              ApprovalMode=SimpleNamespace(deny_all='deny-all'),
                              TextInput=lambda text: {'text': text}, ImageInput=lambda url: {'image': url})
        return sdk, client, thread

    def test_status_uses_selected_file_store_and_never_inherits_api_keys(self):
        result = subprocess.CompletedProcess([], 0, b'Logged in using ChatGPT\n')
        with patch('openai_connection.find_codex', return_value='synthetic-codex'), \
                patch('openai_connection.subprocess.run', return_value=result) as run, \
                patch('openai_connection.importlib.util.find_spec', return_value=True), \
                patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-key', 'CODEX_API_KEY': 'synthetic-key',
                                        'CODEX_ACCESS_TOKEN': 'synthetic-token'}):
            self.assertTrue(self.connection.status()['canTest'])
        self.assertEqual(run.call_args.args[0], ['synthetic-codex', '-c',
                         'cli_auth_credentials_store="file"', 'login', 'status'])
        self.assertEqual(run.call_args.kwargs['timeout'], 8)
        environment = run.call_args.kwargs['env']
        self.assertEqual(environment['CODEX_HOME'], str(self.connection.home))
        self.assertFalse({'OPENAI_API_KEY', 'CODEX_API_KEY', 'CODEX_ACCESS_TOKEN'} & environment.keys())

    def test_refresh_recognizes_external_sign_in_after_an_earlier_failed_attempt(self):
        self.connection._state = 'failed'
        with patch.object(self.connection, '_status', return_value=('signed_in', 'Connected.')), \
                patch('openai_connection.importlib.util.find_spec', return_value=True):
            self.assertTrue(self.connection.status()['canTest'])

    def test_login_preserves_existing_unconfirmed_account(self):
        self.connection.home.mkdir()
        auth = self.connection.home / 'auth.json'
        auth.write_text('{"synthetic":true}', encoding='utf-8')
        with patch.object(self.connection, '_status', return_value=('unavailable', 'Unconfirmed.')), \
                patch('openai_connection.subprocess.Popen') as launch:
            with self.assertRaises(AssessmentError) as caught:
                self.connection.start_login()
        self.assertEqual(caught.exception.status, 409)
        launch.assert_not_called()
        self.assertEqual(auth.read_text(encoding='utf-8'), '{"synthetic":true}')

    def test_generation_preserves_model_effort_schema_images_and_closes_the_client(self):
        self.connection.home.mkdir()
        (self.connection.home / 'config.toml').write_text('[mcp_servers.synthetic]\ncommand="unused"\n', encoding='utf-8')
        sdk, client, thread = self.synthetic_sdk()
        schema = {'type': 'object'}
        with patch.dict(sys.modules, {'openai_codex': sdk}), \
                patch('openai_connection.find_codex', return_value='synthetic-codex'):
            result = asyncio.run(self.connection._generate(SELECTION, 'prompt', 'instructions', schema, ('image-url',)))
        self.assertEqual(result, 'review text')
        config = sdk.AsyncCodex.call_args.args[0]
        self.assertEqual(config.codex_bin, 'synthetic-codex')
        self.assertEqual(config.env['CODEX_HOME'], str(self.connection.home))
        self.assertIn('mcp_servers.synthetic.enabled=false', config.config_overrides)
        client.thread_start.assert_awaited_once_with(model=SELECTION['model'], model_provider='openai',
            sandbox='read-only', approval_mode='deny-all', ephemeral=True, developer_instructions='instructions')
        thread.run.assert_awaited_once_with([{'text': 'prompt'}, {'image': 'image-url'}],
            model=SELECTION['model'], output_schema=schema, effort='xhigh', sandbox='read-only', approval_mode='deny-all')
        client.close.assert_awaited_once()

    def test_failed_and_interrupted_sdk_runs_close_and_do_not_claim_success(self):
        for failure in ('incomplete', TimeoutError(), RuntimeError('synthetic provider detail')):
            sdk, client, thread = self.synthetic_sdk()
            if isinstance(failure, Exception):
                thread.run.side_effect = failure
            else:
                thread.run.return_value.status = SimpleNamespace(value=failure)
            with self.subTest(failure=type(failure).__name__), \
                    patch.dict(sys.modules, {'openai_codex': sdk}), \
                    patch.object(self.connection, 'status', return_value={'canTest': True}), \
                    patch('openai_connection.find_codex', return_value='synthetic-codex'):
                with self.assertRaises(AssessmentError) as caught:
                    self.connection.infer(SELECTION, 'prompt', 'instructions', None)
            self.assertNotIn('synthetic provider detail', str(caught.exception))
            client.close.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
