"""Tests for process launch flags and connection-refusal diagnostics."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import process_launch


class ProcessLaunchTest(TestCase):
	def test_windows_start_uses_breakaway_flag(self):
		with patch.object(process_launch.os, 'name', 'nt'), \
			patch.object(process_launch.subprocess, 'CREATE_NEW_PROCESS_GROUP',
				0x200, create=True), \
			patch.object(process_launch.subprocess, 'DETACHED_PROCESS',
				0x8, create=True), \
			patch.object(process_launch.subprocess, 'CREATE_BREAKAWAY_FROM_JOB',
				0x1000000, create=True), \
			patch.object(
				process_launch.subprocess, 'Popen',
				return_value='process') as popen:
			self.assertEqual('process', process_launch.detached_popen(
				['fman'], cwd='C:/fman'))
		popen.assert_called_once_with(['fman'], cwd='C:/fman',
			creationflags=0x200 | 0x8 | 0x1000000)

	def test_windows_access_denied_retries_without_breakaway(self):
		denied = OSError('access denied')
		denied.winerror = 5
		with patch.object(process_launch.os, 'name', 'nt'), \
			patch.object(process_launch.subprocess, 'CREATE_NEW_PROCESS_GROUP',
				0x200, create=True), \
			patch.object(process_launch.subprocess, 'DETACHED_PROCESS',
				0x8, create=True), \
			patch.object(process_launch.subprocess, 'CREATE_BREAKAWAY_FROM_JOB',
				0x1000000, create=True), \
			patch.object(process_launch.subprocess, 'Popen',
				side_effect=[denied, 'fallback']) as popen:
			self.assertEqual(
				'fallback', process_launch.detached_popen(
					['fman']))
		self.assertEqual([
			0x200 | 0x8 | 0x1000000,
			0x200 | 0x8,
		], [call.kwargs['creationflags'] for call in popen.call_args_list])

	def test_windows_other_start_error_propagates(self):
		error = OSError('not permitted')
		with patch.object(process_launch.os, 'name', 'nt'), \
			patch.object(process_launch.subprocess, 'CREATE_NEW_PROCESS_GROUP',
				0x200, create=True), \
			patch.object(process_launch.subprocess, 'DETACHED_PROCESS',
				0x8, create=True), \
			patch.object(process_launch.subprocess, 'CREATE_BREAKAWAY_FROM_JOB',
				0x1000000, create=True), \
			patch.object(
				process_launch.subprocess, 'Popen', side_effect=error) as popen:
			with self.assertRaisesRegex(OSError, 'not permitted'):
				process_launch.detached_popen(['fman'])
		popen.assert_called_once()

	def test_describe_refused_reports_exited_process_and_log_tail(self):
		with TemporaryDirectory() as temp:
			profile = Path(temp) / 'profile'
			Path(temp, 'fman.log').write_text('last line\n', encoding='utf-8')
			session = {
				'session_id': 'session-x', 'pid': 1234, 'start_time': 10,
				'fman_pid': 1234, 'fman_start_time': 10,
				'port': 8765, 'profile': str(profile),
			}
			missing = process_launch.psutil.NoSuchProcess(1234)
			with patch.object(process_launch.psutil, 'Process', side_effect=missing):
				message = process_launch.describe_refused(session)
		self.assertIn('fman (pid 1234) of session session-x has exited', message)
		self.assertIn('last line', message)

	def test_describe_refused_reports_running_process_on_port(self):
		process = Mock()
		process.create_time.return_value = 10
		with TemporaryDirectory() as temp:
			session = {
				'session_id': 'session-y', 'pid': 4321, 'start_time': 10,
				'port': 9876, 'profile': str(Path(temp) / 'profile'),
			}
			with patch.object(process_launch.psutil, 'Process',
				return_value=process):
				message = process_launch.describe_refused(session)
		self.assertEqual(
			'fman (pid 4321) of session session-y is running but refuses '
			'connections on port 9876', message)


if __name__ == '__main__':
	main()
