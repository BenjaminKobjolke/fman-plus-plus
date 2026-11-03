"""Command for listing processes that lock selected local files or folders."""
from fman import DirectoryPaneCommand, NO, PLATFORM, YES, show_alert, \
	show_status_message
from fman.url import as_human_readable

from core.commands.util import chosen_files, is_file_url
from core.fs.local.lock_finder import find_locking_processes, list_files


__all__ = ['FindLockingProcesses']

CONFIRM_FILE_COUNT = 100
STATUS_MESSAGE = 'Finding files to check...'
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
		show_status_message(STATUS_MESSAGE)
		files = list_files(paths)
		if len(files) > CONFIRM_FILE_COUNT:
			message = CONFIRM_MESSAGE % len(files)
			if not (show_alert(message, YES | NO, YES) & YES):
				return
		processes = find_locking_processes(paths, files)
		if processes:
			show_alert('\n'.join(
				RESULT_LINE % (process.name, process.pid, process.reason)
				for process in processes
			))
		else:
			show_alert(NO_LOCKING_PROCESS_MESSAGE)
