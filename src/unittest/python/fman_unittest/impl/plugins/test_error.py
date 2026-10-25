import io
import unittest
from unittest.mock import Mock, patch

from PyQt5.QtWidgets import QMessageBox

from fman.impl.console_log import ConsoleLog
from fman.impl.plugins.error import PluginErrorHandler


class PluginErrorHandlerTest(unittest.TestCase):
	def setUp(self):
		self.console_log = ConsoleLog()
		self.open_console = Mock()
		self.handler = PluginErrorHandler(
			Mock(), self.console_log, self.open_console
		)
		self.window = Mock()
		self.handler.on_main_window_shown(self.window)

	def test_logs_full_error_and_shows_headline_only_alert(self):
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
		self.assertEqual(args[0], 'Plugin raised an error.')
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
		self.assertEqual(args[0], 'First error.')
		self.assertEqual(window.show_alert.call_count, 1)


if __name__ == '__main__':
	unittest.main()
