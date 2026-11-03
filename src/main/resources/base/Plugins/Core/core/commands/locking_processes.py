"""Command for listing processes that lock selected local files or folders."""
from fman import DirectoryPaneCommand, NO, PLATFORM, YES, Task, submit_task
from fman.url import as_human_readable

from core.commands.util import chosen_files, is_file_url
from core.fs.local.lock_finder import find_locking_processes, list_files


__all__ = ['FindLockingProcesses']

CONFIRM_FILE_COUNT = 100
TASK_TITLE = 'Finding locking processes'
COLLECTING_FILES = 'Collecting files: {:,}'
CHECKING_FILES = 'Checking {:,} files'
CONFIRM_MESSAGE = '%d files to check. This may take a while. Continue?'
RESULT_LINE = '%s (PID %d) %s'
NO_LOCKING_PROCESS_MESSAGE = (
	'No locking process found. Processes running as administrator and open '
	'folder handles (e.g. Explorer) are not visible.'
)


class FindLockingProcesses(DirectoryPaneCommand):
	aliases = ('Find locking processes',)

	def is_visible(self):
		return PLATFORM == 'Windows' and is_file_url(self.pane.get_path())

	def __call__(self):
		urls = chosen_files(self)
		if not urls:
			return
		paths = [
			as_human_readable(url) for url in urls if is_file_url(url)
		]
		submit_task(_FindLocks(paths))


class _FindLocks(Task):
	minimizable = True

	def __init__(self, paths):
		super().__init__(TASK_TITLE)
		self._paths = paths

	def __call__(self):
		def report_file_count(count):
			self.check_canceled()
			self.set_text(COLLECTING_FILES.format(count))

		files = list_files(self._paths, on_progress=report_file_count)
		if len(files) > CONFIRM_FILE_COUNT:
			message = CONFIRM_MESSAGE % len(files)
			if not (self.show_alert(message, YES | NO, YES) & YES):
				return

		self.set_size(len(files))
		self.set_text(CHECKING_FILES.format(len(files)))

		def report_check_progress(files_done):
			self.check_canceled()
			self.set_progress(files_done)

		processes = find_locking_processes(
			self._paths, files, on_progress=report_check_progress
		)
		if processes:
			self.show_alert('\n'.join(
				RESULT_LINE % (process.name, process.pid, process.reason)
				for process in processes
			))
		else:
			self.show_alert(NO_LOCKING_PROCESS_MESSAGE)
