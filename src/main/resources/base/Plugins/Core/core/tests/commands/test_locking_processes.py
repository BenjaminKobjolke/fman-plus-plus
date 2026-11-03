from unittest import TestCase
from unittest.mock import patch

from fman import NO, Task, YES
from fman.url import as_url

from core.commands import FindLockingProcesses as RegisteredFindLockingProcesses
from core.commands.locking_processes import (
	CONFIRM_FILE_COUNT,
	CONFIRM_MESSAGE,
	FindLockingProcesses,
	NO_LOCKING_PROCESS_MESSAGE,
	RESULT_LINE,
	_FindLocks,
)
from core.fs.local.lock_finder import LockingProcess


class FindLockingProcessesTest(TestCase):
	def setUp(self):
		self.pane = type('Pane', (), {'get_path': lambda self: as_url(r'C:\folder')})()
		self.command = FindLockingProcesses(self.pane)
		self.assertIs(RegisteredFindLockingProcesses, FindLockingProcesses)

	def test_declining_large_selection_skips_finding_processes(self):
		files = ['file-%d.txt' % i for i in range(CONFIRM_FILE_COUNT + 1)]
		task = _FindLocks([r'C:\folder'])
		with (
			patch('core.commands.locking_processes.list_files', return_value=files),
			patch.object(task, 'show_alert', return_value=NO) as show_alert,
			patch(
				'core.commands.locking_processes.find_locking_processes'
			) as find_processes,
		):
			task()

		show_alert.assert_called_once_with(
			CONFIRM_MESSAGE % len(files), YES | NO, YES
		)
		find_processes.assert_not_called()

	def test_result_message_lists_each_process(self):
		files = [r'C:\folder\file.txt']
		processes = [
			LockingProcess(1234, 'Code.exe', 'has a file open'),
			LockingProcess(4321, 'cmd.exe', 'has its working directory inside'),
		]
		task = _FindLocks([r'C:\folder'])
		with (
			patch('core.commands.locking_processes.list_files', return_value=files),
			patch(
				'core.commands.locking_processes.find_locking_processes',
				return_value=processes,
			),
			patch.object(task, 'show_alert') as show_alert,
		):
			task()

		show_alert.assert_called_once_with(
			RESULT_LINE % ('Code.exe', 1234, 'has a file open') + '\n' +
			RESULT_LINE % ('cmd.exe', 4321, 'has its working directory inside')
		)

	def test_reports_when_no_process_is_found(self):
		task = _FindLocks([r'C:\folder'])
		with (
			patch('core.commands.locking_processes.list_files', return_value=[]),
			patch(
				'core.commands.locking_processes.find_locking_processes',
				return_value=[],
			),
			patch.object(task, 'show_alert') as show_alert,
		):
			task()

		show_alert.assert_called_once_with(NO_LOCKING_PROCESS_MESSAGE)

	def test_canceled_progress_hook_stops_before_finding_processes(self):
		task = _FindLocks([r'C:\folder'])
		task._dialog._was_canceled = True

		def list_files(paths, on_progress):
			on_progress(1)

		with (
			patch('core.commands.locking_processes.list_files', side_effect=list_files),
			patch(
				'core.commands.locking_processes.find_locking_processes'
			) as find_processes,
		):
			with self.assertRaises(Task.Canceled):
				task()

		find_processes.assert_not_called()

	def test_command_submits_a_find_locks_task(self):
		with (
			patch('core.commands.locking_processes.chosen_files', return_value=[
				as_url(r'C:\folder'), 'https://example.com/file',
			]),
			patch('core.commands.locking_processes.submit_task') as submit_task,
		):
			self.command()

		task = submit_task.call_args.args[0]
		self.assertIsInstance(task, _FindLocks)
		self.assertEqual([r'C:\folder'], task._paths)
