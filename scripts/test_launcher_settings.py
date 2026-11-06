"""Selected settings reach the launcher child and cannot reuse another profile's engine."""
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from connection_settings import SettingsError
import launch_math_practice as launcher


class LauncherSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.settings = MagicMock()
        self.settings.path = self.root / 'lesson-profile.yaml'
        self.settings.path.write_text('{}', encoding='utf-8')
        self.root_patch = patch.object(launcher, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.settings_patch = patch('connection_settings.ConnectionSettings', return_value=self.settings)
        self.factory = self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.open_patch = patch.object(launcher.OPENER, 'open')
        self.request = self.open_patch.start()
        self.request.return_value.__enter__.return_value = io.BytesIO(b'{}')
        self.addCleanup(self.open_patch.stop)
        self.browser_patch = patch.object(launcher.webbrowser, 'open')
        self.browser = self.browser_patch.start()
        self.addCleanup(self.browser_patch.stop)

    def running(self, **changes):
        return {'pid': 123, 'settingsInstance': launcher.engine_instance(self.settings.path), **changes}

    def test_selected_profile_is_validated_and_passed_to_hidden_child_as_absolute_path(self):
        selected = Path('saved profiles') / 'lesson-profile.yaml'
        with patch.object(launcher, 'engine', side_effect=[None, self.running()]), \
             patch.object(launcher, 'port_available', return_value=True), \
             patch.object(launcher.subprocess, 'Popen') as start:
            result = launcher.launch(8899, False, selected)
        self.factory.assert_called_once_with(selected)
        args = start.call_args.args[0]
        self.assertEqual(args[-4:], ['--port', '8899', '--settings', str(self.settings.path.resolve())])
        self.assertEqual(start.call_args.kwargs['creationflags'], subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.assertEqual(start.call_args.kwargs['start_new_session'], os.name != 'nt')
        self.assertEqual(start.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(result, {'url': 'http://127.0.0.1:8899/math-practice/', 'pid': 123})
        self.browser.assert_not_called()
        self.assertTrue(self.request.call_args.args[0].full_url.endswith('/api/settings/reload'))

    def test_matching_profile_reuses_engine_without_starting_another_process(self):
        with patch.object(launcher, 'engine', return_value=self.running()), \
             patch.object(launcher.subprocess, 'Popen') as start:
            result = launcher.launch(settings_path=self.settings.path)
        start.assert_not_called()
        self.browser.assert_called_once_with(result['url'])
        self.assertEqual(self.request.call_count, 1)

    def test_different_profile_cannot_be_reused_or_reloaded(self):
        for selected in (None, self.settings.path):
            with self.subTest(selected=selected), \
                 patch.object(launcher, 'engine', return_value=self.running(settingsInstance='other-profile')), \
                 patch.object(launcher.subprocess, 'Popen') as start:
                with self.assertRaisesRegex(RuntimeError, 'selected settings file.*another port.*restart'):
                    launcher.launch(settings_path=selected)
                start.assert_not_called()
        self.request.assert_not_called()
        self.browser.assert_not_called()

    def test_explicit_profile_requires_engine_settings_identity(self):
        with patch.object(launcher, 'engine', return_value={'pid': 123}), \
             self.assertRaisesRegex(RuntimeError, 'selected settings file'):
            launcher.launch(settings_path=self.settings.path)
        self.request.assert_not_called()
        self.browser.assert_not_called()

    def test_legacy_default_call_still_accepts_probe_without_settings_identity(self):
        with patch.object(launcher, 'engine', return_value={'pid': 123}):
            result = launcher.launch(open_browser=False)
        self.factory.assert_called_once_with(None)
        self.assertEqual(result['pid'], 123)
        self.assertEqual(self.request.call_count, 1)

    def test_identity_is_checked_again_while_waiting_for_a_new_engine(self):
        with patch.object(launcher, 'engine', side_effect=[None, self.running(settingsInstance='other-profile')]), \
             patch.object(launcher, 'port_available', return_value=True), \
             patch.object(launcher.subprocess, 'Popen'), \
             self.assertRaisesRegex(RuntimeError, 'selected settings file'):
            launcher.launch(settings_path=self.settings.path)
        self.request.assert_not_called()
        self.browser.assert_not_called()

    def test_invalid_selected_settings_fail_before_engine_or_process_access(self):
        self.factory.side_effect = SettingsError('Check lesson-profile.yaml for valid settings.')
        with patch.object(launcher, 'engine') as probe, \
             patch.object(launcher.subprocess, 'Popen') as start, \
             self.assertRaisesRegex(RuntimeError, 'lesson-profile.yaml'):
            launcher.launch(settings_path=self.settings.path)
        probe.assert_not_called()
        start.assert_not_called()
        self.request.assert_not_called()

    def test_missing_explicit_profile_errors_while_default_still_creates_settings(self):
        self.settings.path.unlink()
        with patch.object(launcher, 'engine') as probe, \
             self.assertRaises(RuntimeError) as failure:
            launcher.launch(settings_path=self.settings.path)
        self.assertIn(str(self.settings.path), str(failure.exception))
        self.assertIn('does not exist', str(failure.exception))
        self.settings.save.assert_not_called()
        probe.assert_not_called()
        self.request.assert_not_called()
        with patch.object(launcher, 'engine', return_value={'pid': 123}):
            launcher.launch(open_browser=False)
        self.settings.save.assert_called_once_with({})
        self.assertEqual(self.request.call_count, 1)

    def test_reload_failure_names_the_selected_settings_file(self):
        self.request.side_effect = OSError('fixture')
        with patch.object(launcher, 'engine', return_value=self.running()), \
             self.assertRaisesRegex(RuntimeError, 'reload lesson-profile.yaml'):
            launcher.launch(settings_path=self.settings.path)
        self.browser.assert_not_called()

    def test_cli_forwards_selected_profile_port_and_no_open(self):
        with patch.object(launcher.sys, 'argv', ['launch_math_practice.py', '--settings', 'later.yaml', '--port', '8899', '--no-open']), \
             patch.object(launcher, 'launch', return_value={'url': 'fixture', 'pid': 123}) as launch, \
             patch.object(launcher.sys, 'stdout', new_callable=io.StringIO) as output:
            status = launcher.main()
        self.assertEqual(status, 0)
        launch.assert_called_once_with(8899, False, Path('later.yaml'))
        self.assertEqual(json.loads(output.getvalue())['pid'], 123)


if __name__ == '__main__':
    unittest.main()
