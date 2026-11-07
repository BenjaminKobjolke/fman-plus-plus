from unittest import TestCase
from unittest.mock import Mock, patch

from core.palette_switch import (
	COMMAND_PALETTE, GO_TO, palette_exit_keys, run_palette_switch,
)
from fman import QuicksearchExit


class PaletteExitKeysTest(TestCase):
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
	def test_runs_other_palette_with_current_query(self):
		pane = Mock(spec=['run_command'])
		exit = QuicksearchExit('abc', GO_TO)

		run_palette_switch(pane, exit)

		pane.run_command.assert_called_once_with(GO_TO, {'query': 'abc'})
