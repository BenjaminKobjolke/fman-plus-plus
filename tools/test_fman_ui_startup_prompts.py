"""Tests for reading startup prompt state from an isolated fman session."""

from pathlib import Path
import sys
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
from startup_prompts import read_startup_prompts


class StartupPromptsTest(TestCase):
	def test_waits_for_window_then_reads_startup_and_dialog(self):
		states = iter((
			{'startup': {'window_shown': False}},
			{'startup': {
				'window_shown': True,
				'demo_mode': True,
				'update_check_scheduled': False,
			}},
		))
		calls = []

		def api(session, method, path):
			calls.append((method, path))
			if path == '/v1/state':
				return next(states)
			return {'dialog': {'type': 'MessageBox'}}

		with patch('startup_prompts.time.sleep') as sleep:
			result = read_startup_prompts({'port': 123}, api)

		self.assertEqual({
			'demo_mode': True,
			'update_check_scheduled': False,
			'dialog': {'type': 'MessageBox'},
		}, result)
		self.assertEqual([
			('GET', '/v1/state'), ('GET', '/v1/state'),
			('GET', '/v1/dialog'),
		], calls)
		sleep.assert_called_once_with(0.1)

	def test_raises_if_window_is_not_reported_before_deadline(self):
		with patch('startup_prompts.time.monotonic', side_effect=(0, 0, 10.1)), \
			patch('startup_prompts.time.sleep'), \
			self.assertRaisesRegex(
				RuntimeError, 'fman did not report its startup within 10 s'):
			read_startup_prompts(
				{'port': 123}, lambda *args: {'startup': {'window_shown': False}})
