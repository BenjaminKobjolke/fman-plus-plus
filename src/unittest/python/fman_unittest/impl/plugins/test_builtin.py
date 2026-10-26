from fman import DirectoryPane
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
		scripting_control = MagicMock()
		with patch.object(
			BuiltinPlugin, '_register_application_command',
			side_effect=commands.append
		), patch.object(BuiltinPlugin, '_register_directory_pane_command'), \
			patch.object(BuiltinPlugin, '_register_file_system'), \
			patch.object(BuiltinPlugin, '_register_column'), \
			patch('fman.impl.plugins.builtin.is_mac', return_value=False):
			BuiltinPlugin(None, None, None, window_chrome, scripting_control, *args)

		by_name = {command.__name__: command for command in commands}
		self.assertIn('ToggleIncognito', by_name)
		self.assertEqual(
			commands.index(by_name['ToggleIncognito']),
			commands.index(by_name['ToggleStatusBar']) + 1)

		window = MagicMock()
		left = MagicMock(spec=DirectoryPane)
		right = MagicMock(spec=DirectoryPane)
		left.get_path.return_value = 'file://C:/a'
		left.get_file_under_cursor.return_value = 'file://C:/a/x.txt'
		right.get_path.return_value = 'file://C:/b'
		right.get_file_under_cursor.return_value = None
		window.get_panes.return_value = [left, right]
		command = by_name['ToggleIncognito'](window)

		command()
		left.set_path.assert_not_called()
		right.set_path.assert_not_called()
		left.get_path.return_value = 'file://C:/elsewhere-a'
		right.get_path.return_value = 'file://C:/elsewhere-b'
		left.place_cursor_at.side_effect = ValueError
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
		self.assertEqual(left.set_path.call_count, 1)
		self.assertEqual(right.set_path.call_count, 1)
		self.assertEqual(left.set_path.call_args.args[0], 'file://C:/a')
		self.assertEqual(right.set_path.call_args.args[0], 'file://C:/b')
		left.set_path.call_args.args[1]()
		right.set_path.call_args.args[1]()
		left.place_cursor_at.assert_called_once_with('file://C:/a/x.txt')
		right.place_cursor_at.assert_not_called()
		self.assertEqual((), incognito.get_pane_states())

	def test_toggle_scripting_api_shows_controller_message(self):
		commands = []
		window_chrome = MagicMock()
		scripting_control = MagicMock()
		scripting_control.toggle.return_value = 'Scripting API on'
		args = [MagicMock() for _ in range(7)]
		with patch.object(
			BuiltinPlugin, '_register_application_command',
			side_effect=commands.append
		), patch.object(BuiltinPlugin, '_register_directory_pane_command'), \
			patch.object(BuiltinPlugin, '_register_file_system'), \
			patch.object(BuiltinPlugin, '_register_column'), \
			patch('fman.impl.plugins.builtin.is_mac', return_value=False):
			BuiltinPlugin(None, None, None, window_chrome, scripting_control, *args)

		by_name = {command.__name__: command for command in commands}
		command_class = by_name['ToggleScriptingApi']
		self.assertEqual(('Toggle scripting API',), command_class.aliases)
		window = MagicMock()
		command = command_class(window)
		command_class.__call__.__wrapped__(command)
		scripting_control.toggle.assert_called_once_with()
		window._widget.show_status_message.assert_called_once_with(
			'Scripting API on')
