import io
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from PyQt5.QtWidgets import QMessageBox

from fman.impl.application_context import DevelopmentApplicationContext
from fman.impl.console_log import ConsoleLog
from fman.impl.plugins.error import PluginErrorHandler


class FakeAppErrorReporter:
	def __init__(self, enabled):
		self.is_enabled = enabled
		self.send = Mock(return_value=True)
	def create_report(self, exc, kind='unhandled', plugin=None):
		return {'kind': kind, 'plugin': plugin, 'message': str(exc)}


class PluginErrorHandlerTest(unittest.TestCase):
	def setUp(self):
		self.console_log = ConsoleLog()
		self.open_console = Mock()
		self.handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console
		)
		self.window = Mock()
		self.handler.on_main_window_shown(self.window)

	def test_logs_full_error_and_shows_exception_line_in_alert(self):
		exc = ValueError('details')
		self.window.show_alert.return_value = QMessageBox.Cancel
		stderr = io.StringIO()

		with patch('fman.impl.plugins.error.is_frozen', return_value=False), \
			patch('fman.impl.plugins.error.sys.__stderr__', stderr):
			self.handler.report('Plugin raised an error.', exc)

		entry = self.console_log.entries[-1]
		self.assertIn('Plugin raised an error.', entry)
		self.assertIn('ValueError: details', entry)
		self.assertIn('ValueError: details', stderr.getvalue())
		args, kwargs = self.window.show_alert.call_args
		self.assertEqual(
			args[0], 'Plugin raised an error.\n\nValueError: details'
		)
		self.assertEqual(kwargs['button_texts'], {
			QMessageBox.Cancel: 'Dismiss',
			QMessageBox.Open: 'Open in console',
			QMessageBox.Save: 'Copy error'
		})

	def test_open_in_console_action_invokes_callback(self):
		self.window.show_alert.return_value = QMessageBox.Open

		self.handler.report('Plugin raised an error.', ValueError('details'))

		self.open_console.assert_called_once_with()

	def test_exception_hook_passes_exception_into_console_report(self):
		exc = ValueError('details')
		with patch.object(
			self.handler, '_get_plugin_causing_error', return_value='/plugins/Test'
		), patch('fman.impl.plugins.error.is_frozen', return_value=True):
			self.handler.handle(ValueError, exc, None)

		self.assertIn('ValueError: details', self.console_log.entries[-1])

	def test_copy_action_copies_full_error_and_shows_status(self):
		self.window.show_alert.return_value = QMessageBox.Save

		with patch('fman.impl.plugins.error.fman.clipboard.set_text') as set_text:
			self.handler.report('Plugin raised an error.', ValueError('details'))

		set_text.assert_called_once()
		self.assertIn('Plugin raised an error.', set_text.call_args.args[0])
		self.assertIn('ValueError: details', set_text.call_args.args[0])
		self.window.show_status_message.assert_called_once()

	def test_startup_errors_are_logged_and_only_first_is_alerted(self):
		handler = PluginErrorHandler(Mock(), self.console_log, self.open_console)

		handler.report('First error.', ValueError('first'))
		handler.report('Second error.', ValueError('second'))
		window = Mock()
		handler.on_main_window_shown(window)

		self.assertEqual(len(self.console_log.entries), 2)
		args, _ = window.show_alert.call_args
		self.assertEqual(args[0], 'First error.\n\nValueError: first')
		self.assertEqual(window.show_alert.call_count, 1)

	def test_report_writes_traceback_to_log_file(self):
		with tempfile.TemporaryDirectory() as directory:
			log_path = os.path.join(directory, 'Errors.log')
			handler = PluginErrorHandler(
				Mock(), self.console_log, self.open_console, log_path
			)
			handler.report('Plugin raised an error.', ValueError('details'))

			with open(log_path) as log_file:
				contents = log_file.read()
		self.assertIn('Plugin raised an error.', contents)
		self.assertIn('ValueError: details', contents)

	def test_first_report_truncates_existing_log_only_once_per_process(self):
		with tempfile.TemporaryDirectory() as directory:
			log_path = os.path.join(directory, 'Errors.log')
			with open(log_path, 'w') as log_file:
				log_file.write('old error')
			first_handler = PluginErrorHandler(
				Mock(), self.console_log, self.open_console, log_path
			)
			first_handler.report('First error.', ValueError('first'))
			second_handler = PluginErrorHandler(
				Mock(), self.console_log, self.open_console, log_path
			)
			second_handler.report('Second error.', ValueError('second'))

			with open(log_path) as log_file:
				contents = log_file.read()
		self.assertNotIn('old error', contents)
		self.assertIn('ValueError: first', contents)
		self.assertIn('ValueError: second', contents)

	def test_concurrent_reports_write_complete_entries_without_losing_first(self):
		with tempfile.TemporaryDirectory() as directory:
			log_path = os.path.join(directory, 'Errors.log')
			handler = PluginErrorHandler(
				Mock(), self.console_log, self.open_console, log_path
			)
			messages = ['Error %d' % index for index in range(20)]
			with ThreadPoolExecutor(max_workers=len(messages)) as executor:
				list(executor.map(handler._write_error_log, messages))

			with open(log_path) as log_file:
				contents = log_file.read().splitlines()

		for message in messages:
			self.assertEqual(contents.count(message), 1)

	def test_unwritable_log_path_does_not_hide_plugin_error(self):
		handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console, 'Errors.log'
		)
		with patch('builtins.open', side_effect=OSError('denied')):
			handler.report('Plugin raised an error.', ValueError('details'))

		self.assertIn('ValueError: details', self.console_log.entries[-1])

	def test_open_console_opens_error_log_without_core_command(self):
		context = Mock()
		context.pane_command_registry.get_commands.return_value = set()
		context._get_local_data_file.return_value = 'local/Errors.log'

		with patch(
			'fman.impl.application_context.QUrl.fromLocalFile',
			return_value='file-url'
		) as from_local_file, patch(
			'fman.impl.application_context.QDesktopServices.openUrl'
		) as open_url:
			DevelopmentApplicationContext._open_console_from_error(context)

		context._get_local_data_file.assert_called_once_with('Errors.log')
		from_local_file.assert_called_once_with('local/Errors.log')
		open_url.assert_called_once_with('file-url')

	def test_plugin_error_is_reported_with_plugin_name_when_enabled(self):
		reporter = FakeAppErrorReporter(True)
		handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console,
			app_error_reporter=reporter
		)
		handler.on_main_window_shown(self.window)
		exc = ValueError('details')
		self.window.show_alert.return_value = QMessageBox.Cancel

		with patch.object(
			handler, '_get_plugin_causing_error', return_value='/plugins/Example'
		), patch('fman.impl.plugins.error.is_frozen', return_value=True):
			self.assertTrue(handler.handle(ValueError, exc, None))

		reporter.send.assert_called_once_with({
			'kind': 'plugin', 'plugin': 'Example', 'message': 'details'
		})
		self.assertEqual(self.window.show_alert.call_count, 1)
		self.assertFalse(
			int(self.window.show_alert.call_args.kwargs['buttons']) &
			int(QMessageBox.Apply)
		)

	def test_core_error_is_sent_unhandled_when_enabled_without_alert(self):
		reporter = FakeAppErrorReporter(True)
		handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console,
			app_error_reporter=reporter
		)
		exc = ValueError('details')

		with patch.object(
			handler, '_get_plugin_causing_error', return_value='/plugins/Core'
		):
			self.assertIsNone(handler.handle(ValueError, exc, None))

		reporter.send.assert_called_once_with({
			'kind': 'unhandled', 'plugin': None, 'message': 'details'
		})
		self.window.show_alert.assert_not_called()

	def test_core_error_shows_manual_send_button_when_reporting_disabled(self):
		reporter = FakeAppErrorReporter(False)
		handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console,
			app_error_reporter=reporter
		)
		handler.on_main_window_shown(self.window)
		exc = ValueError('details')
		self.window.show_alert.return_value = QMessageBox.Cancel

		with patch.object(
			handler, '_get_plugin_causing_error', return_value='/plugins/Core'
		), patch('fman.impl.plugins.error.is_frozen', return_value=True):
			self.assertIsNone(handler.handle(ValueError, exc, None))

		self.assertTrue(
			int(self.window.show_alert.call_args.kwargs['buttons']) &
			int(QMessageBox.Apply)
		)
		self.assertIn(
			QMessageBox.Apply,
			self.window.show_alert.call_args.kwargs['button_texts']
		)
		self.assertEqual(self.window.show_alert.call_count, 1)
		reporter.send.assert_not_called()

	def test_manual_send_changes_kind_and_shows_status(self):
		reporter = FakeAppErrorReporter(False)
		handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console,
			app_error_reporter=reporter
		)
		handler.on_main_window_shown(self.window)
		self.window.show_alert.return_value = QMessageBox.Apply

		handler.report('Error.', ValueError('details'), {
			'kind': 'unhandled', 'message': 'details'
		})

		reporter.send.assert_called_once_with({
			'kind': 'manual', 'message': 'details'
		})
		self.window.show_status_message.assert_called_once_with(
			'Error report sent.', timeout_secs=3
		)

	def test_queued_error_keeps_its_report_for_manual_sending(self):
		reporter = FakeAppErrorReporter(False)
		handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console,
			app_error_reporter=reporter
		)
		saved_report = {'kind': 'unhandled', 'message': 'details'}
		handler.report('Error.', ValueError('details'), saved_report)
		self.assertEqual(handler._pending_errors[0][2], saved_report)

		window = Mock()
		window.show_alert.return_value = QMessageBox.Apply
		handler.on_main_window_shown(window)

		reporter.send.assert_called_once_with({
			'kind': 'manual', 'message': 'details'
		})

	def test_core_errors_remain_silent_without_reporter(self):
		with patch.object(
			self.handler, '_get_plugin_causing_error', return_value='/plugins/Core'
		):
			self.assertIsNone(
				self.handler.handle(ValueError, ValueError('details'), None)
			)
		self.window.show_alert.assert_not_called()


if __name__ == '__main__':
	unittest.main()
