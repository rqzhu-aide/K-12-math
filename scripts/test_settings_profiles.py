"""Settings profiles preserve key-file references and explicit model roles."""
import builtins
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from connection_settings import ConnectionSettings, SettingsError
from student_assessment import ANSWER_CORRECTNESS, CORRECTNESS, ModelConfig, RUBRICS


HAS_YAML = importlib.util.find_spec('yaml') is not None


class SettingsProfileTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.path = self.folder / 'config.json'
        self.key = 'synthetic-private-key-for-profile-tests'
        (self.folder / 'key.txt').write_text(self.key + '\n', encoding='utf-8')

    def profile(self):
        return {'decision': {'bases': ['http://127.0.0.1:9951'], 'model': 'd3-mini',
                             'protocol': 'systemone', 'apiKeyFile': 'key.txt'},
                'speech': {'bases': ['http://127.0.0.1:9934'], 'model': 'qwen3-asr', 'apiKeyFile': 'key.txt'},
                'inference': {'provider': 'api', 'bases': ['https://provider.example/v1'],
                              'model': 'math-model', 'apiKeyFile': 'key.txt'},
                'mathAssessment': 'inference'}

    def write_json(self, document=None):
        self.path.write_text(json.dumps(self.profile() if document is None else document), encoding='utf-8')

    def assert_private(self, value):
        encoded = json.dumps(value)
        self.assertNotIn(self.key, encoded)
        self.assertNotIn('apiKeyFile', encoded)
        self.assertNotIn('key.txt', encoded)

    @unittest.skipUnless(HAS_YAML, 'Install PyYAML globally to exercise YAML profiles.')
    def test_yaml_loads_relative_files_for_all_three_roles(self):
        import yaml
        self.path = self.folder / 'setting.yaml'
        self.path.write_text(yaml.safe_dump(self.profile()), encoding='utf-8')
        settings = ConnectionSettings(self.path, defaults=ModelConfig())
        self.assertEqual(settings.decision_config().api_key, self.key)
        self.assertEqual(settings.speech_config().api_key, self.key)
        self.assertEqual(settings.inference_config()['apiKey'], self.key)
        self.assertEqual(settings.math_assessment_provider(), 'inference')
        self.assertEqual(settings.public()['mathAssessment'], 'inference')
        self.assert_private(settings.public())

    @unittest.skipUnless(HAS_YAML, 'Install PyYAML globally to exercise YAML profiles.')
    def test_yaml_save_keeps_references_and_route_without_copying_keys(self):
        import yaml
        self.path = self.folder / 'setting.yml'
        self.path.write_text(yaml.safe_dump(self.profile()), encoding='utf-8')
        settings = ConnectionSettings(self.path)
        settings.save({'decision': {'model': 'd3-mini-next', 'apiKey': ''}})
        document = yaml.safe_load(self.path.read_text(encoding='utf-8'))
        for role in ('decision', 'speech', 'inference'):
            self.assertEqual(document[role]['apiKeyFile'], 'key.txt')
            self.assertNotIn('apiKey', document[role])
        self.assertNotIn(self.key, self.path.read_text(encoding='utf-8'))
        loaded = ConnectionSettings(self.path)
        self.assertEqual(loaded.math_assessment_provider(), 'inference')
        self.assertEqual(loaded.decision_config().model, 'd3-mini-next')
        self.assertEqual(loaded.decision_config().api_key, self.key)

    def test_json_keeps_existing_references_when_other_settings_are_saved(self):
        self.write_json()
        settings = ConnectionSettings(self.path)
        settings.save({'inference': {'effort': 'high'}})
        document = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(document['mathAssessment'], 'inference')
        for role in ('decision', 'speech', 'inference'):
            self.assertEqual(document[role]['apiKeyFile'], 'key.txt')
            self.assertNotIn('apiKey', document[role])
        self.assert_private(settings.public())

    def test_explicit_replacement_key_removes_only_that_roles_reference(self):
        self.write_json()
        settings = ConnectionSettings(self.path)
        settings.save({'decision': {'apiKey': 'synthetic-replacement'}})
        document = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(document['decision']['apiKey'], 'synthetic-replacement')
        self.assertNotIn('apiKeyFile', document['decision'])
        self.assertEqual(document['speech']['apiKeyFile'], 'key.txt')
        self.assertEqual(document['inference']['apiKeyFile'], 'key.txt')
        self.assertEqual(ConnectionSettings(self.path).decision_config().api_key, 'synthetic-replacement')

    def test_changing_destination_does_not_reuse_a_saved_file_key(self):
        self.write_json()
        settings = ConnectionSettings(self.path)
        settings.save({'speech': {'bases': ['http://127.0.0.2:9934'], 'apiKey': ''}})
        document = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(document['speech']['apiKey'], '')
        self.assertNotIn('apiKeyFile', document['speech'])
        self.assertEqual(ConnectionSettings(self.path).speech_config().api_key, '')

    def test_new_file_reference_can_be_saved_and_compared_without_publishing_it(self):
        settings = ConnectionSettings(self.path, defaults=ModelConfig())
        settings.save(self.profile())
        (self.folder / 'other.txt').write_text(self.key, encoding='utf-8')
        draft = {'decision': {'apiKeyFile': 'other.txt'}}
        compared = settings.compare_file(draft)
        self.assertEqual(compared['changedSections'], ['decision'])
        self.assert_private(compared)
        settings.save(draft)
        self.assertEqual(json.loads(self.path.read_text())['decision']['apiKeyFile'], 'other.txt')
        self.assertFalse(settings.compare_file(draft)['different'])

    def test_file_key_rotation_is_detected_and_reloaded(self):
        self.write_json()
        settings = ConnectionSettings(self.path)
        before = settings.public()['decision']['keyRevision']
        (self.folder / 'key.txt').write_text('synthetic-rotated-key', encoding='utf-8')
        compared = settings.compare_file({'decision': {'apiKey': ''}})
        self.assertEqual(compared['changedSections'], ['decision'])
        self.assertNotEqual(compared['keyRevisions']['decision'], before)
        self.assertEqual(settings.decision_config().api_key, self.key)
        settings.reload()
        self.assertEqual(settings.decision_config().api_key, 'synthetic-rotated-key')
        settings.save({'decision': {'apiKey': ''}})
        self.assertNotIn('apiKey', json.loads(self.path.read_text())['decision'])

    def test_missing_key_file_error_does_not_echo_its_path_or_key(self):
        document = self.profile()
        document['decision']['apiKeyFile'] = self.key + '.txt'
        self.write_json(document)
        with self.assertRaises(SettingsError) as raised:
            ConnectionSettings(self.path)
        self.assertIn('decision API key file could not be read', str(raised.exception))
        self.assertNotIn(self.key, str(raised.exception))

    def test_empty_or_multiline_key_file_is_rejected_without_echoing_contents(self):
        self.write_json()
        for value in ('  \n', self.key + '\nsecond-line'):
            with self.subTest(empty=not value.strip()):
                (self.folder / 'key.txt').write_text(value, encoding='utf-8')
                with self.assertRaises(SettingsError) as raised:
                    ConnectionSettings(self.path)
                self.assertNotIn(self.key, str(raised.exception))

    def test_inline_key_and_file_reference_cannot_silently_disagree(self):
        document = self.profile()
        document['decision']['apiKey'] = self.key
        self.write_json(document)
        with self.assertRaises(SettingsError) as raised:
            ConnectionSettings(self.path)
        self.assertIn('either an API key or an API key file', str(raised.exception))
        self.assertNotIn(self.key, str(raised.exception))

    @unittest.skipUnless(HAS_YAML, 'Install PyYAML globally to exercise YAML profiles.')
    def test_malformed_yaml_and_unsafe_tags_are_sanitized(self):
        self.path = self.folder / 'setting.yaml'
        for value in ('decision: [\napiKey: ' + self.key,
                      '!!python/object/apply:os.system [' + self.key + ']'):
            with self.subTest(unsafe=value.startswith('!!')):
                self.path.write_text(value, encoding='utf-8')
                with self.assertRaises(SettingsError) as raised:
                    ConnectionSettings(self.path)
                self.assertIn('valid YAML', str(raised.exception))
                self.assertNotIn(self.key, str(raised.exception))

    def test_json_stays_dependency_free_and_missing_yaml_has_install_instruction(self):
        original_import = builtins.__import__

        def import_without_yaml(name, *args, **kwargs):
            if name == 'yaml':
                raise ImportError('synthetic missing package')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=import_without_yaml):
            settings = ConnectionSettings(self.path, defaults=ModelConfig())
            settings.save({'mathAssessment': 'inference'})
            self.assertEqual(ConnectionSettings(self.path).math_assessment_provider(), 'inference')
            self.path = self.folder / 'setting.yaml'
            self.path.write_text('mathAssessment: inference\n', encoding='utf-8')
            with self.assertRaises(SettingsError) as raised:
                ConnectionSettings(self.path)
            self.assertIn('python -m pip install --user PyYAML', str(raised.exception))

    def test_route_defaults_to_legacy_and_persists_through_save_compare_and_reload(self):
        settings = ConnectionSettings(self.path, defaults=ModelConfig())
        self.assertEqual(settings.math_assessment_provider(), 'decision')
        self.assertEqual(settings.public()['mathAssessment'], 'decision')
        self.assertEqual(settings.compare_file({'mathAssessment': 'inference'})['changedSections'], ['mathAssessment'])
        settings.save({'mathAssessment': 'inference'})
        settings.save({'inference': {'provider': 'codex', 'model': 'account-model'}})
        self.assertFalse(settings.compare_file({'mathAssessment': 'inference'})['different'])
        document = json.loads(self.path.read_text())
        document['mathAssessment'] = 'decision'
        self.path.write_text(json.dumps(document), encoding='utf-8')
        self.assertEqual(settings.compare_file({})['changedSections'], ['mathAssessment'])
        self.assertEqual(settings.reload()['mathAssessment'], 'decision')
        self.assertEqual(settings.math_assessment_provider(), 'decision')

    def test_invalid_route_does_not_modify_saved_or_active_settings(self):
        settings = ConnectionSettings(self.path, defaults=ModelConfig())
        settings.save({'mathAssessment': 'inference'})
        before = self.path.read_bytes()
        for value in ('speech', '', None, True, {}):
            with self.subTest(value=value), self.assertRaises(SettingsError):
                settings.save({'mathAssessment': value})
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(settings.math_assessment_provider(), 'inference')

    def test_inference_route_probes_only_the_three_learning_signals(self):
        settings = ConnectionSettings(self.path, defaults=ModelConfig())
        settings.save(self.profile())
        with patch('connection_settings.StudentAssessment._decide', return_value={}) as decide:
            result = settings.test_decision({})
        self.assertTrue(result['ready'])
        self.assertEqual(decide.call_count, 1)
        self.assertEqual(decide.call_args.args[1], RUBRICS)
        self.assertIn('all three learning signals', result['message'])
        self.assertNotIn('mathematical reasoning assessment', result['message'])

    def test_default_route_keeps_all_three_probe_contracts_and_draft_can_override(self):
        settings = ConnectionSettings(self.path, defaults=ModelConfig())
        document = self.profile()
        document.pop('mathAssessment')
        settings.save(document)
        with patch('connection_settings.StudentAssessment._decide', return_value={}) as decide:
            settings.test_decision({})
        self.assertEqual([call.args[1] for call in decide.call_args_list], [RUBRICS, CORRECTNESS, ANSWER_CORRECTNESS])
        with patch('connection_settings.StudentAssessment._decide', return_value={}) as decide:
            settings.test_decision({'mathAssessment': 'inference'})
        self.assertEqual(decide.call_count, 1)
        self.assertEqual(settings.math_assessment_provider(), 'decision')


if __name__ == '__main__':
    unittest.main()
