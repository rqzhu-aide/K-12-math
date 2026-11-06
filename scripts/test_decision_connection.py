"""Decision connection tests cover the rubrics used for signals and reasoning."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from connection_settings import ConnectionSettings
from student_assessment import AssessmentError, ANSWER_CORRECTNESS, CORRECTNESS, ModelConfig, RUBRICS


def chat_reply(rubrics):
    observations = {name: {'code': next(iter(rubric['options'].values()))[0],
                           'evidence': 'The submitted text provides this evidence.'}
                    for name, rubric in rubrics.items()}
    return {'choices': [{'message': {'content': json.dumps(observations)}}]}


def legacy_reply(questions):
    return {'answers': {name: {'probabilities': {key: int(index == 0)
                                               for index, key in enumerate(question['criteria'])}}
                        for name, question in questions.items()}}


class DecisionConnectionTests(unittest.TestCase):
    def setUp(self):
        self.settings = ConnectionSettings(Path(__file__).with_name('_unused_connection_config.json'), defaults=ModelConfig())

    def configured(self, protocol):
        return patch.object(self.settings, 'decision_config', return_value=ModelConfig(
            ('https://provider.example/v1',), 'decision-test-model', 'test-key', protocol))

    def test_chat_checks_production_signals_reasoning_and_typed_answer(self):
        with self.configured('chat'), patch('model_connections.request', side_effect=[
                chat_reply(RUBRICS), chat_reply(CORRECTNESS), chat_reply(ANSWER_CORRECTNESS)]) as request:
            result = self.settings.test_decision({})
        self.assertTrue(result['ready'])
        self.assertEqual(result['model'], 'decision-test-model')
        self.assertIn('all three learning signals', result['message'])
        self.assertIn('mathematical reasoning', result['message'])
        self.assertEqual(request.call_count, 3)
        bodies = [json.loads(call.args[2]) for call in request.call_args_list]
        for body, expected in zip(bodies, (RUBRICS, CORRECTNESS, ANSWER_CORRECTNESS)):
            rubrics = json.loads(body['messages'][0]['content'].split('Rubrics:\n', 1)[1])
            self.assertEqual(set(rubrics), set(expected))
            for name, rubric in expected.items():
                self.assertEqual(rubrics[name]['instructions'], rubric['instructions'])
            self.assertEqual(body['response_format'], {'type': 'json_object'})
        self.assertNotIn('Reference solution', bodies[0]['messages'][1]['content'])
        self.assertIn('Student reasoning', bodies[1]['messages'][1]['content'])

    def test_legacy_checks_same_rubrics_through_the_production_protocol(self):
        def reply(config, route, body, content_type, timeout=None):
            self.assertEqual(route, '/v1/systemone')
            return legacy_reply(json.loads(body)['questions'])

        with self.configured('systemone'), patch('model_connections.request', side_effect=reply) as request:
            result = self.settings.test_jev({})
        self.assertTrue(result['ready'])
        self.assertEqual([call.args[1] for call in request.call_args_list],
                         ['/v1/systemone'] * 3)
        for call, expected in zip(request.call_args_list, (RUBRICS, CORRECTNESS, ANSWER_CORRECTNESS)):
            questions = json.loads(call.args[2])['questions']
            self.assertEqual(set(questions), set(expected))
            for name, rubric in expected.items():
                self.assertEqual(questions[name]['instructions'], rubric['instructions'])
                self.assertEqual(questions[name]['criteria'], {key: value[2] for key, value in rubric['options'].items()})

    def test_chat_cannot_succeed_on_signals_alone(self):
        with self.configured('chat'), patch('model_connections.request', side_effect=[
                chat_reply(RUBRICS), chat_reply(RUBRICS)]) as request, \
                self.assertRaises(AssessmentError) as raised:
            self.settings.test_decision({})
        self.assertEqual(request.call_count, 2)
        self.assertEqual(raised.exception.status, 502)
        self.assertIn('mathematical reasoning', str(raised.exception))
        self.assertNotIn('work is saved', str(raised.exception))

    def test_chat_cannot_succeed_without_the_typed_answer_contract(self):
        with self.configured('chat'), patch('model_connections.request', side_effect=[
                chat_reply(RUBRICS), chat_reply(CORRECTNESS), chat_reply(CORRECTNESS)]) as request, \
                self.assertRaises(AssessmentError) as raised:
            self.settings.test_decision({})
        self.assertEqual(request.call_count, 3)
        self.assertIn('typed answer', str(raised.exception))

    def test_invalid_signals_stop_before_the_reasoning_request(self):
        with self.configured('chat'), patch('model_connections.request', return_value=chat_reply(CORRECTNESS)) as request, \
                self.assertRaises(AssessmentError) as raised:
            self.settings.test_decision({})
        self.assertEqual(request.call_count, 1)
        self.assertIn('learning signals', str(raised.exception))

    def test_legacy_rejects_the_old_custom_connection_only_response(self):
        old_probe = {'answers': {'connection': {'choice': 'a', 'probabilities': {'a': 1, 'b': 0}}}}
        with self.configured('systemone'), patch('model_connections.request', return_value=old_probe) as request, \
                self.assertRaises(AssessmentError) as raised:
            self.settings.test_decision({})
        self.assertEqual(request.call_count, 1)
        self.assertIn('learning signals', str(raised.exception))

    def test_unconfigured_connection_makes_no_requests(self):
        with patch.object(self.settings, 'decision_config', return_value=ModelConfig()), \
             patch('student_assessment.OPENER.open', side_effect=AssertionError('No network request expected')):
            result = self.settings.test_decision({})
        self.assertFalse(result['configured'])
        self.assertFalse(result['ready'])


if __name__ == '__main__':
    unittest.main()
