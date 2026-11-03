from unittest import TestCase
from unittest.mock import patch

from fman import NO, YES
from fman.url import as_url

from core.commands import FindLockingProcesses as RegisteredFindLockingProcesses
from core.commands.locking_processes import (
	CONFIRM_FILE_COUNT,
	FindLockingProcesses,
)
from core.fs.local.lock_finder import LockingProcess


class FindLockingProcessesTest(TestCase):
	def setUp(self):
		self.pane = type('Pane', (), {'get_path': lambda self: as_url(r'C:\folder')})()
		self.command = FindLockingProcesses(self.pane)
		self.assertIs(RegisteredFindLockingProcesses, FindLockingProcesses)

	def test_declines_checking_more_than_one_hundred_files(self):
		files = ['file-%d.txt' % i for i in range(CONFIRM_FILE_COUNT + 1)]
		with (
			patch('core.commands.locking_processes.PLATFORM', 'Windows'),
			patch(
				'core.commands.locking_processes.chosen_files',
				return_value=[as_url(r'C:\folder')],
			),
			patch('core.commands.locking_processes.list_files', return_value=files),
			patch('core.commands.locking_processes.show_status_message'),
			patch(
				'core.commands.locking_processes.show_alert', return_value=NO
			) as show_alert,
			patch(
				'core.commands.locking_processes.find_locking_processes'
			) as find_processes,
		):
			self.command()

		show_alert.assert_called_once_with(
			'%d files to check. This may take a while. Continue?' % len(files),
			YES | NO,
			YES,
		)
		find_processes.assert_not_called()

	def test_result_message_lists_each_process(self):
		files = [r'C:\folder\file.txt']
		processes = [
			LockingProcess(1234, 'Code.exe', 'has a file open'),
			LockingProcess(4321, 'cmd.exe', 'has its working directory inside'),
		]
		with (
			patch('core.commands.locking_processes.PLATFORM', 'Windows'),
			patch(
				'core.commands.locking_processes.chosen_files',
				return_value=[as_url(r'C:\folder')],
			),
			patch('core.commands.locking_processes.list_files', return_value=files),
			patch(
				'core.commands.locking_processes.find_locking_processes',
				return_value=processes,
			),
			patch('core.commands.locking_processes.show_status_message'),
			patch('core.commands.locking_processes.show_alert') as show_alert,
		):
			self.command()

		show_alert.assert_called_once_with(
			'Code.exe (PID 1234) has a file open\n'
			'cmd.exe (PID 4321) has its working directory inside'
		)

	def test_reports_when_no_process_is_found(self):
		with (
			patch('core.commands.locking_processes.PLATFORM', 'Windows'),
			patch(
				'core.commands.locking_processes.chosen_files',
				return_value=[as_url(r'C:\folder')],
			),
			patch('core.commands.locking_processes.list_files', return_value=[]),
			patch(
				'core.commands.locking_processes.find_locking_processes',
				return_value=[],
			),
			patch('core.commands.locking_processes.show_status_message'),
			patch('core.commands.locking_processes.show_alert') as show_alert,
		):
			self.command()

		show_alert.assert_called_once_with(
			'No locking process found. Processes running as administrator and open '
			'folder handles (e.g. Explorer) are not visible.'
		)
