from fman import DirectoryPane
from fman.impl import incognito
from fman.impl.application_context import DevelopmentApplicationContext
from fman.impl.incognito import OFF_MESSAGE, ON_INCOGNITO_CHANGED, ON_MESSAGE
from fman.impl.plugins.builtin import BuiltinPlugin
from unittest import TestCase
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch
from PyQt5.QtWidgets import QMessageBox


class ToggleIncognitoTest(TestCase):
	def setUp(self):
		incognito.set_incognito(False)
		self.addCleanup(incognito.set_incognito, False)

	def _registered_commands(self, scripting_control, local_settings=None):
		commands = []
		with patch.object(
			BuiltinPlugin, '_register_application_command',
			side_effect=commands.append
		), patch.object(BuiltinPlugin, '_register_directory_pane_command'), \
			patch.object(BuiltinPlugin, '_register_file_system'), \
			patch.object(BuiltinPlugin, '_register_column'), \
			patch('fman.impl.plugins.builtin.is_mac', return_value=False):
			BuiltinPlugin(
				None, None, None, MagicMock(), scripting_control, None,
				*(MagicMock() for _ in range(7)),
				local_settings=local_settings or MagicMock()
			)
		return commands, {command.__name__: command for command in commands}

	def test_toggle_notifies_both_panes_and_updates_the_marker_and_message(self):
		commands, by_name = self._registered_commands(MagicMock())
		self.assertIn('ToggleIncognito', by_name)
		self.assertEqual(
			commands.index(by_name['ToggleIncognito']),
			commands.index(by_name['ToggleRightButtonSelection']) + 1)

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
		scripting_control = MagicMock()
		scripting_control.toggle.return_value = 'Scripting API on'
		_, by_name = self._registered_commands(scripting_control)
		command_class = by_name['ToggleScriptingApi']
		self.assertEqual(('Toggle scripting API',), command_class.aliases)
		window = MagicMock()
		command = command_class(window)
		command_class.__call__.__wrapped__(command)
		scripting_control.toggle.assert_called_once_with()
		window._widget.show_status_message.assert_called_once_with(
			'Scripting API on')

	def test_toggle_error_reports_flips_and_flushes_setting(self):
		settings = MagicMock()
		settings.get.side_effect = [False, True]
		_, commands = self._registered_commands(MagicMock(), settings)
		command_class = commands['ToggleErrorReports']
		self.assertEqual(('Toggle error reports',), command_class.aliases)
		window = MagicMock()
		command = command_class(window)

		command()
		command()

		self.assertEqual(
			settings.__setitem__.call_args_list,
			[call('error_reports', True), call('error_reports', False)])
		self.assertEqual(settings.flush.call_count, 2)
		self.assertEqual(
			window._widget.show_status_message.call_args_list,
			[call('Error reporting on.'), call('Error reporting off.')])

	def test_error_report_consent_is_deferred_until_after_first_run(self):
		context = self._startup_context(first_run=True)

		DevelopmentApplicationContext.on_main_window_shown(context)

		context.tour_controller.start.assert_called_once()
		context.main_window.show_alert.assert_not_called()

	def test_error_report_consent_saves_yes_and_flushes(self):
		context = self._startup_context(first_run=False)
		context.main_window.show_alert.return_value = QMessageBox.Yes

		DevelopmentApplicationContext.on_main_window_shown(context)

		context.main_window.show_alert.assert_called_once()
		self.assertEqual(
			context.main_window.show_alert.call_args.args[0],
			'Would you like to send error reports? They help a lot to improve fman.')
		self.assertEqual(
			context.main_window.show_alert.call_args.kwargs['default_button'],
			QMessageBox.No)
		self.assertEqual(
			context.main_window.show_alert.call_args.kwargs['button_texts'],
			{QMessageBox.Yes: 'Yes', QMessageBox.No: 'No'})
		context.local_settings.__setitem__.assert_called_once_with(
			'error_reports', True)
		context.local_settings.flush.assert_called_once_with()

	def test_closing_error_report_consent_saves_no_and_flushes(self):
		context = self._startup_context(first_run=False)
		context.main_window.show_alert.return_value = QMessageBox.Cancel

		DevelopmentApplicationContext.on_main_window_shown(context)

		context.local_settings.__setitem__.assert_called_once_with(
			'error_reports', False)
		context.local_settings.flush.assert_called_once_with()

	def test_error_report_consent_is_not_repeated_after_answer(self):
		context = self._startup_context(first_run=False, error_reports=True)

		DevelopmentApplicationContext.on_main_window_shown(context)

		context.main_window.show_alert.assert_not_called()

	def test_demo_mode_does_not_show_startup_prompts(self):
		context = self._startup_context(first_run=False)
		context._demo_mode = True

		DevelopmentApplicationContext.on_main_window_shown(context)

		context.update_check_timer.start.assert_not_called()
		context.main_window.show_alert.assert_not_called()

	@staticmethod
	def _startup_context(first_run, error_reports=None):
		settings = MagicMock()
		settings.get.return_value = error_reports
		context = SimpleNamespace(
			_demo_mode=False,
			main_window=MagicMock(),
			update_check_timer=MagicMock(),
			session_manager=SimpleNamespace(is_first_run=first_run),
			plugin_support=SimpleNamespace(get_panes=lambda: [MagicMock()]),
			tutorial_factory=lambda pane: MagicMock(),
			tour_controller=MagicMock(),
			local_settings=settings,
		)
		context._ask_error_report_consent = lambda: \
			DevelopmentApplicationContext._ask_error_report_consent(context)
		return context
