from fman.impl import incognito
from fman.impl.incognito import OFF_MESSAGE, ON_INCOGNITO_CHANGED, ON_MESSAGE
from fman.impl.plugins.builtin import BuiltinPlugin
from unittest import TestCase
from unittest.mock import MagicMock, call, patch


class ToggleIncognitoTest(TestCase):
	def setUp(self):
		incognito.set_incognito(False)
		self.addCleanup(incognito.set_incognito, False)

	def test_toggle_notifies_both_panes_and_updates_the_marker_and_message(self):
		commands = []
		window_chrome = MagicMock()
		args = [MagicMock() for _ in range(7)]
		with patch.object(
			BuiltinPlugin, '_register_application_command',
			side_effect=commands.append
		), patch.object(BuiltinPlugin, '_register_directory_pane_command'), \
			patch.object(BuiltinPlugin, '_register_file_system'), \
			patch.object(BuiltinPlugin, '_register_column'), \
			patch('fman.impl.plugins.builtin.is_mac', return_value=False):
			BuiltinPlugin(None, None, None, window_chrome, *args)

		by_name = {command.__name__: command for command in commands}
		self.assertIn('ToggleIncognito', by_name)
		self.assertEqual(
			commands.index(by_name['ToggleIncognito']),
			commands.index(by_name['ToggleStatusBar']) + 1)

		window = MagicMock()
		left, right = MagicMock(), MagicMock()
		window.get_panes.return_value = [left, right]
		command = by_name['ToggleIncognito'](window)

		command()
		command()

		self.assertEqual(
			[left._broadcast.call_args_list, right._broadcast.call_args_list],
			[[call(ON_INCOGNITO_CHANGED, True),
			  call(ON_INCOGNITO_CHANGED, False)]] * 2)
		self.assertEqual(
			window._widget.set_incognito_marker_visible.call_args_list,
			[call(True), call(False)])
		self.assertEqual(
			window._widget.show_status_message.call_args_list,
			[call(ON_MESSAGE), call(OFF_MESSAGE)])
