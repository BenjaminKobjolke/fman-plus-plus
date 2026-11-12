from unittest import TestCase
from unittest.mock import Mock, patch

from core.palette_switch import (
	COMMAND_PALETTE, GO_TO, goto_query_exit, palette_exit_keys,
	palette_query_exit, run_palette_switch, strip_command_prefix,
)
from fman import QuicksearchExit


class PaletteExitKeysTest(TestCase):
	def test_strips_only_a_leading_command_prefix(self):
		self.assertEqual('copy', strip_command_prefix('>copy'))
		self.assertEqual('copy>', strip_command_prefix('copy>'))
	def test_goto_switches_when_prefix_is_typed(self):
		self.assertEqual(COMMAND_PALETTE, goto_query_exit('>'))
		self.assertIsNone(goto_query_exit('copy'))
	def test_palette_switches_back_when_prefix_is_removed(self):
		self.assertEqual(GO_TO, palette_query_exit(''))
		self.assertEqual(GO_TO, palette_query_exit('copy'))
		self.assertIsNone(palette_query_exit('>copy'))
	def test_maps_other_palette_shortcuts_and_own_shortcuts_to_close(self):
		bindings = [
			{'keys': ['Ctrl+P'], 'command': GO_TO},
			{'keys': ['Ctrl+Shift+P'], 'command': COMMAND_PALETTE},
		]
		with patch('core.palette_switch.load_json', return_value=bindings):
			result = palette_exit_keys(COMMAND_PALETTE, GO_TO)

		self.assertEqual({
			'Ctrl+P': GO_TO,
			'Ctrl+Shift+P': None,
		}, result)

	def test_follows_user_shortcut_override(self):
		bindings = [
			{'keys': ['Ctrl+G'], 'command': GO_TO},
			{'keys': ['Ctrl+Shift+P'], 'command': COMMAND_PALETTE},
		]
		with patch('core.palette_switch.load_json', return_value=bindings):
			result = palette_exit_keys(COMMAND_PALETTE, GO_TO)

		self.assertEqual(GO_TO, result['Ctrl+G'])
		self.assertNotIn('Ctrl+P', result)


class RunPaletteSwitchTest(TestCase):
	def test_runs_other_palette_with_current_query_and_typing_state(self):
		pane = Mock(spec=['run_command'])
		for from_text in (False, True):
			with self.subTest(from_text=from_text):
				pane.reset_mock()
				run_palette_switch(
					pane, QuicksearchExit('abc', GO_TO, from_text=from_text)
				)
				pane.run_command.assert_called_once_with(GO_TO, {
					'query': 'abc', 'continue_typing': from_text
				})
