"""Undo the latest supported file operation from this fman session."""

from core import elevation
from core.commands.deletion import confirm_trash, trash
from core.undo_history import CopyRecord, MoveRecord, RenameRecord, TrashRecord, history
from core.recycle_bin import find_entry, restore_entry
from fman import DirectoryPaneCommand, PLATFORM, Task, show_alert, submit_task
from fman.fs import exists, notify_file_added, prepare_move, samefile
from fman.url import basename, dirname


__all__ = ['Undo']

_NOTHING_TO_UNDO = 'Nothing to undo.'
_TRASH_UNSUPPORTED = (
	'Restoring from the Trash is only supported on Windows. Nothing was restored.'
)


class Undo(DirectoryPaneCommand):
	def __call__(self):
		record = history.pop()
		if record is None:
			show_alert(_NOTHING_TO_UNDO)
		elif isinstance(record, TrashRecord):
			self._undo_trash(record)
		elif isinstance(record, (MoveRecord, RenameRecord)):
			self._undo_moves(record)
		elif isinstance(record, CopyRecord):
			self._undo_copy(record)

	def _undo_trash(self, record):
		if PLATFORM != 'Windows':
			show_alert(_TRASH_UNSUPPORTED)
			return
		failures = []
		for url in record.urls:
			try:
				entry = find_entry(url)
				if entry is None:
					raise FileNotFoundError('No matching Recycle Bin entry')
				restore_entry(entry)
				notify_file_added(url)
			except OSError as error:
				failures.append(_failure(url, error))
		if failures:
			show_alert('Some items could not be restored:\n' + '\n'.join(failures))

	def _undo_moves(self, record):
		failures = []
		for src_url, dst_url in record.urls:
			try:
				if exists(src_url) and not samefile(src_url, dst_url):
					raise FileExistsError('The original location is occupied')
				if not exists(dst_url):
					raise FileNotFoundError('The moved file no longer exists')
				if not elevation.move(
					[dst_url], dirname(src_url), basename(src_url)
				):
					submit_task(_MoveBack(dst_url, src_url))
				_place_cursor_at(self.pane, src_url)
			except OSError as error:
				failures.append(_failure(dst_url, error))
		if failures:
			show_alert('Some items could not be moved back:\n' + '\n'.join(failures))

	def _undo_copy(self, record):
		urls = [dst_url for _, dst_url in record.urls if exists(dst_url)]
		if not urls:
			return
		if confirm_trash(urls):
			trash(urls, undoable=False)
		else:
			history.record(record)


class _MoveBack(Task):
	def __init__(self, src_url, dst_url):
		self._src_url = src_url
		self._dst_url = dst_url
		super().__init__('Moving ' + basename(src_url) + ' back')

	def __call__(self):
		tasks = list(prepare_move(self._src_url, self._dst_url))
		self.set_size(sum(task.get_size() for task in tasks))
		for task in tasks:
			self.check_canceled()
			self.run(task)


def _failure(url, error):
	name = basename(url)
	reason = getattr(error, 'strerror', None) or str(error)
	return '{}: {}'.format(name, reason)


def _place_cursor_at(pane, url):
	try:
		pane.place_cursor_at(url)
	except ValueError:
		pass
