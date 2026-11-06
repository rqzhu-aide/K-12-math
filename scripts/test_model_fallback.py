"""Fallback time budgets use deterministic clocks and never contact a service."""
import io
import unittest
from unittest.mock import patch

import model_connections
from student_assessment import AssessmentError, ModelConfig


class ModelFallbackTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.calls = []
        self.clock = patch('model_connections.time.monotonic', side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def config(self, bases):
        return ModelConfig(tuple(bases), 'fixture-model', 'synthetic-fixture-key')

    def request(self, config, timeout=60):
        return model_connections.request(config, '/v1/chat/completions', b'{}', 'application/json', timeout)

    def test_blackholed_first_address_leaves_time_for_lan(self):
        bases = ['http://tailscale.example:9951/v1', 'http://192.0.2.10:9951/v1']

        def open_request(request, timeout):
            self.calls.append((request.full_url, timeout))
            if len(self.calls) == 1:
                self.now += timeout
                raise TimeoutError('Synthetic unreachable address')
            self.now += 2
            return io.BytesIO(b'{"ready": true}')

        with patch.object(model_connections.OPENER, 'open', side_effect=open_request):
            self.assertEqual(self.request(self.config(bases)), {'ready': True})
        self.assertEqual(self.calls, [(bases[0] + '/chat/completions', 30),
                                     (bases[1] + '/chat/completions', 30)])
        self.assertEqual(self.now, 132)

    def test_configured_order_and_last_address_gets_all_remaining_time(self):
        bases = ['http://tailscale.example:9951', 'http://100.64.0.10:9951', 'http://192.0.2.10:9951']

        def open_request(request, timeout):
            self.calls.append((request.full_url, timeout))
            self.assertEqual(request.get_header('Authorization'), 'Bearer synthetic-fixture-key')
            if len(self.calls) == 1:
                self.now += timeout
                raise TimeoutError('Synthetic unreachable DNS endpoint')
            if len(self.calls) == 2:
                self.now += 5
                raise OSError('Synthetic unavailable Tailscale IP')
            return io.BytesIO(b'{"ready": true}')

        with patch.object(model_connections.OPENER, 'open', side_effect=open_request):
            self.assertEqual(self.request(self.config(bases)), {'ready': True})
        self.assertEqual([url for url, _ in self.calls], [base + '/v1/chat/completions' for base in bases])
        self.assertEqual([timeout for _, timeout in self.calls], [20, 20, 35])

    def test_single_endpoint_keeps_full_inference_timeout(self):
        with patch.object(model_connections.OPENER, 'open', return_value=io.BytesIO(b'{}')) as opener:
            self.assertEqual(self.request(self.config(['http://provider.example/v1']), timeout=125), {})
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(opener.call_args.kwargs['timeout'], 125)

    def test_all_blackholed_addresses_use_one_shared_elapsed_budget_without_retries(self):
        config = self.config(['http://one.example', 'http://two.example', 'http://three.example'])

        def open_request(request, timeout):
            self.calls.append((request.full_url, timeout))
            self.now += timeout
            raise TimeoutError('Synthetic unreachable address')

        with patch.object(model_connections.OPENER, 'open', side_effect=open_request), self.assertRaises(AssessmentError) as raised:
            self.request(config, timeout=90)
        self.assertEqual(raised.exception.status, 503)
        self.assertEqual([timeout for _, timeout in self.calls], [30, 30, 30])
        self.assertEqual(self.now, 190)
        self.assertEqual(len(self.calls), len(config.bases))

    def test_elapsed_deadline_stops_fallback_if_system_operation_overruns_timeout(self):
        config = self.config(['http://one.example', 'http://two.example'])

        def open_request(request, timeout):
            self.now += 61  # DNS resolution can outlast urllib's socket timeout.
            raise TimeoutError('Synthetic system lookup overrun')

        with patch.object(model_connections.OPENER, 'open', side_effect=open_request) as opener, self.assertRaises(AssessmentError):
            self.request(config)
        self.assertEqual(opener.call_count, 1)

    def test_successful_first_address_does_not_call_fallbacks(self):
        config = self.config(['http://one.example', 'http://two.example'])
        with patch.object(model_connections.OPENER, 'open', return_value=io.BytesIO(b'{}')) as opener:
            self.assertEqual(self.request(config), {})
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(opener.call_args.args[0].full_url, 'http://one.example/v1/chat/completions')


if __name__ == '__main__':
    unittest.main()
