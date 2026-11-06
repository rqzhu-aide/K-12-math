"""Exercise masked credentials and independent launcher saves with disposable settings."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from connection_settings import ConnectionSettings, SettingsError


class SettingsPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'config.json'
        self.settings = ConnectionSettings(self.path)
        self.role = {'bases': ['https://speech.example'], 'model': 'fixture'}
        self.initial = self.settings.save({'speech': {**self.role, 'apiKey': 'first-fixture-key'}})

    def test_an_external_key_only_edit_invalidates_the_previous_credential(self):
        patch_from_page = {'speech': {**self.role, 'apiKey': ''}}
        ConnectionSettings(self.path).save({'speech': {'apiKey': 'replacement-fixture-key'}})
        comparison = self.settings.compare_file(patch_from_page)
        self.assertEqual(comparison['changedSections'], ['speech'])
        self.assertNotEqual(comparison['keyRevisions']['speech'], self.initial['speech']['keyRevision'])
        self.assertNotIn('fixture-key', json.dumps(comparison))
        selected = self.settings.on_disk().speech_config(patch_from_page)
        self.assertEqual(selected.api_key, 'replacement-fixture-key')
        self.assertEqual(self.settings.speech_config().api_key, 'first-fixture-key')
        self.settings.reload()
        self.assertFalse(self.settings.compare_file(patch_from_page)['different'])

    def test_overlapping_saves_from_two_launchers_keep_both_edits(self):
        first, second = ConnectionSettings(self.path), ConnectionSettings(self.path)
        first_at_replace = threading.Event()
        release_first = threading.Event()
        from os import replace
        def delay_first(source, destination):
            if not first_at_replace.is_set():
                first_at_replace.set()
                if not release_first.wait(3):
                    raise RuntimeError('The test save did not resume')
            return replace(source, destination)
        with patch('connection_settings.os.replace', side_effect=delay_first), ThreadPoolExecutor(2) as pool:
            write1 = pool.submit(first.save, {'inference': {'provider': 'chatgpt', 'model': 'plan-model'}})
            self.assertTrue(first_at_replace.wait(3))
            write2 = pool.submit(second.save, {'speech': {'model': 'changed-speech'}})
            try:
                write2.result(timeout=0.15)
            except TimeoutError:
                pass
            finally:
                release_first.set()
            write1.result(timeout=5)
            write2.result(timeout=5)
        saved = ConnectionSettings(self.path).public()
        self.assertEqual(saved['inference']['model'], 'plan-model')
        self.assertEqual(saved['speech']['model'], 'changed-speech')

    def test_failed_commit_keeps_previous_config_and_cleans_temporary_key(self):
        with patch('connection_settings.os.replace', side_effect=PermissionError('fixture')):
            with self.assertRaises(SettingsError):
                self.settings.save({'speech': {'apiKey': 'unsaved-fixture-key'}})
        self.assertEqual(self.settings.speech_config().api_key, 'first-fixture-key')
        self.assertEqual(ConnectionSettings(self.path).speech_config().api_key, 'first-fixture-key')
        for path in self.path.parent.iterdir():
            if path.is_file():
                self.assertNotIn(b'unsaved-fixture-key', path.read_bytes())
