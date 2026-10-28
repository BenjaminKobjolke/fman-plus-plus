import unittest
from unittest.mock import Mock, patch

import fman
from fman import main
from fman.impl import portable


class SkipInterpreterTeardownTest(unittest.TestCase):
	def test_flushes_streams_and_exits_with_app_code(self):
		stdout, stderr = Mock(), Mock()
		exit_mock, shutdown_mock = self._run_with_streams(stdout, stderr)
		shutdown_mock.assert_called_once_with()
		stdout.flush.assert_called_once_with()
		stderr.flush.assert_called_once_with()
		exit_mock.assert_called_once_with(3)

	def test_exits_when_output_streams_are_absent(self):
		exit_mock, shutdown_mock = self._run_with_streams(None, None)
		shutdown_mock.assert_called_once_with()
		exit_mock.assert_called_once_with(3)

	def test_exits_when_a_stream_flush_fails(self):
		# A closed stream raises ValueError, a broken output pipe OSError.
		for error in (ValueError('closed file'), OSError('broken pipe')):
			for failing in ('stdout', 'stderr'):
				with self.subTest(error=error, failing=failing):
					streams = {'stdout': Mock(), 'stderr': Mock()}
					streams[failing].flush.side_effect = error
					exit_mock, _ = self._run_with_streams(**streams)
					for stream in streams.values():
						stream.flush.assert_called_once_with()
					exit_mock.assert_called_once_with(3)

	def _run_with_streams(self, stdout, stderr):
		original_code = main._skip_interpreter_teardown.exit_code
		try:
			main._skip_interpreter_teardown.exit_code = 3
			with patch.object(main.os, '_exit') as exit_mock, \
				 patch.object(main.logging, 'shutdown') as shutdown_mock, \
				 patch.object(main.sys, 'stdout', stdout), \
				 patch.object(main.sys, 'stderr', stderr):
				main._skip_interpreter_teardown()
		finally:
			main._skip_interpreter_teardown.exit_code = original_code
		return exit_mock, shutdown_mock


class PortableStartupTest(unittest.TestCase):
	def test_unwritable_portable_data_shows_error_and_exits_before_startup(self):
		data_dir = 'portable-data'
		with patch('atexit.register'), \
		 patch(
			 'fman.impl.application_context.get_application_context'
		 ) as get_context, \
			 patch.object(fman, 'DATA_DIRECTORY', data_dir), \
			 patch.object(portable, 'portable_data_directory', return_value=data_dir), \
		 patch.object(
			 portable, 'check_writable', return_value=PermissionError('denied')
		 ), \
			 patch('ctypes.windll', create=True) as windll, \
			 patch.object(main.sys, 'exit') as exit_mock:
			main.main()

		windll.user32.MessageBoxW.assert_called_once()
		self.assertIn(data_dir, windll.user32.MessageBoxW.call_args.args[1])
		self.assertEqual(fman.APP_NAME, windll.user32.MessageBoxW.call_args.args[2])
		self.assertEqual(0x10, windll.user32.MessageBoxW.call_args.args[3])
		get_context.assert_not_called()
		exit_mock.assert_called_once_with(1)

	def test_writable_portable_data_allows_startup(self):
		data_dir = 'portable-data'
		app_context = Mock()
		app_context.run.return_value = 0
		with patch('atexit.register'), \
		 patch(
			 'fman.impl.application_context.get_application_context',
			 return_value=app_context,
		 ) as get_context, \
			 patch.object(fman, 'DATA_DIRECTORY', data_dir), \
			 patch.object(portable, 'portable_data_directory', return_value=data_dir), \
			 patch.object(portable, 'check_writable', return_value=None), \
			 patch.object(main.sys, 'exit') as exit_mock:
			main.main()

		get_context.assert_called_once_with()
		app_context.run.assert_called_once_with()
		exit_mock.assert_called_once_with(0)
