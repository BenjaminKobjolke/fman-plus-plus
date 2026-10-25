from fman.impl.plugins.builtin import BuiltinPlugin
from json import load
from os.path import dirname, join
from unittest import TestCase
from unittest.mock import MagicMock, patch


class BuiltinPaneStatusCommandsTest(TestCase):

	def test_registers_both_pane_status_commands_on_every_platform(self):
		commands = []
		args = [MagicMock() for _ in range(7)]
		window_chrome = MagicMock()
		with patch.object(
			BuiltinPlugin, '_register_application_command',
			side_effect=commands.append
		), patch.object(BuiltinPlugin, '_register_directory_pane_command'), \
			patch.object(BuiltinPlugin, '_register_file_system'), \
			patch.object(BuiltinPlugin, '_register_column'), \
			patch('fman.impl.plugins.builtin.is_mac', return_value=False):
			BuiltinPlugin(None, None, None, window_chrome, *args)

		by_name = {command.__name__: command for command in commands}
		self.assertIn('TogglePaneStatusLines', by_name)
		self.assertIn('TogglePaneMessagesInStatusBar', by_name)

		window = MagicMock()
		by_name['TogglePaneStatusLines'](window)()
		window_chrome.pane_status.toggle_lines_visible.assert_called_once_with(
			window._widget)

		by_name['TogglePaneMessagesInStatusBar'](window)()
		window_chrome.pane_status.toggle_in_status_bar.assert_called_once_with(
			window._widget)

	def test_command_keywords_are_registered(self):
		path = join(
			dirname(dirname(dirname(dirname(dirname(dirname(__file__)))))),
			'src', 'main', 'resources', 'base', 'Plugins', 'Core',
			'Command Keywords.json')
		with open(path, encoding='utf-8') as file:
			keywords = load(file)
		self.assertEqual(
			['pane status lines', 'pane status bar', 'show pane status'],
			keywords['toggle_pane_status_lines'])
		self.assertEqual(
			['pane messages in status bar', 'copy pane messages',
			 'status bar pane messages'],
			keywords['toggle_pane_messages_in_status_bar'])
