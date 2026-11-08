"""Deleting files: "Move to trash" and "Delete permanently".

Both commands ask for confirmation and then hand the work to `_Delete`, a
Task that prepares one sub-task per URL before running any of them - so a
filesystem that cannot delete at all fails before the first file is gone.
"Move to trash" refuses, deleting nothing, on filesystems that do not
implement `prepare_trash` - the user asked for a recoverable delete.
"""
from fman import DirectoryPaneCommand, PLATFORM, show_alert, submit_task, \
	Task, NO, YES, YES_TO_ALL
from fman import translate
from fman.localization_keys import (
	DELETE_CONFIRM, TRASH_CONFIRM, TRASH_LABEL_RECYCLE_BIN, TRASH_LABEL_TRASH,
)
from fman.fs import (
	exists, get_connection_count, get_parallel_deletes, prepare_delete,
	prepare_trash,
)
from core import elevation
from core.commands.util import NO_SELECTION
from core.transfer_workers import DONE, TransferWorkers, WorkerProgress
from core.undo_history import TrashRecord, history
from fman.url import splitscheme
from errno import EBUSY
from io import UnsupportedOperation
from os import strerror
from os.path import basename
from queue import Queue
from threading import Lock

__all__ = ['DeletePermanently', 'MoveToTrash']

_DELETE_UNSUPPORTED = 'Deleting files in {scheme} is not supported.'
_FILE_IN_USE = 'File is in use'
_FILE_IN_USE_WINDOWS_ERRORS = (32, 33)
_TRASH_UNSUPPORTED = (
	'The {trash} is not available in {scheme}. Nothing was deleted. '
	'Use Delete permanently instead.'
)

class MoveToTrash(DirectoryPaneCommand):

	aliases = ('Delete',)

	def __call__(self, urls=None):
		if urls is None:
			urls = self.get_chosen_files()
		if not urls:
			show_alert(NO_SELECTION)
			return
		if confirm_trash(urls):
			trash(urls)
	def is_visible(self):
		return bool(self.pane.get_file_under_cursor())

# Split out of the command __call__ methods so the in-pane viewers can reuse
# their confirmation and deletion machinery (core/viewer_file_ops.py). Two
# functions per command because the viewer has to confirm first, move its
# cursor off the doomed file and only then submit - _Delete runs in the
# background, so a delete submitted before the cursor moves races the pane
# model. Deliberately not in __all__, which keeps them from being picked up as
# commands.
def confirm_trash(urls):
	description = _describe(urls, 'these %d files')
	trash_name = _trash_name()
	msg = \
	translate(TRASH_CONFIRM) % (description, trash_name)
	return bool(show_alert(msg, YES | NO, YES) & YES)

def confirm_delete(urls):
	description = _describe(urls, 'these %d items')
	message = \
	translate(DELETE_CONFIRM) % description
	return bool(show_alert(
		message, YES | NO, YES,
		button_texts={YES: 'Delete', NO: 'Cancel'}
	) & YES)

def _trash_name():
	key = TRASH_LABEL_RECYCLE_BIN if PLATFORM == 'Windows' else TRASH_LABEL_TRASH
	return translate(key)

def trash(urls, undoable=True):
	if not elevation.delete(urls, to_trash=True):
		submit_task(_Delete(urls, prepare_trash, _TRASH_UNSUPPORTED))
	if undoable:
		deleted_urls = tuple(
			url for url in urls
			if splitscheme(url)[0] == 'file://' and not exists(url)
		)
		if deleted_urls:
			history.record(TrashRecord(deleted_urls))

def delete(urls):
	if not elevation.delete(urls, to_trash=False):
		submit_task(_Delete(urls, prepare_delete))

class DeletePermanently(DirectoryPaneCommand):
	def __call__(self, urls=None):
		if urls is None:
			urls = self.get_chosen_files()
		if not urls:
			show_alert(NO_SELECTION)
			return
		if confirm_delete(urls):
			delete(urls)

class _Delete(Task):
	minimizable = True

	def __init__(self, urls, prepare_fn, unsupported=_DELETE_UNSUPPORTED):
		super().__init__('Deleting ' + _describe(urls))
		self._urls = urls
		self._num_urls_prepared = 0
		self._prepare_fn = prepare_fn
		self._unsupported = unsupported
		self._tasks = []
		self._progress_lock = Lock()
		self._alert_lock = Lock()
		self._ignore_errors = False
		self._worker_count = 1
	def __call__(self):
		try:
			self._gather_tasks()
		except (UnsupportedOperation, NotImplementedError):
			failing_url = self._urls[self._num_urls_prepared]
			self.show_alert(
				self._unsupported.format(
					scheme=splitscheme(failing_url)[0], trash=_trash_name()
				)
			)
			return
		self._worker_count = get_parallel_deletes(self._urls[0])
		queue = Queue()
		for task in self._tasks:
			queue.put(task)
		queue.put(DONE)
		workers = TransferWorkers(
			self._worker_count, queue, self._run_one,
			connection_count=lambda: get_connection_count(self._urls[0])
		)
		if self._worker_count > 1:
			self.set_text(self.get_title())
			self.show_workers(workers)
		workers.start()
		workers.join()
	def _run_one(self, worker, task, is_last):
		self.check_canceled()
		progress = WorkerProgress(
			self._dialog, self._progress_lock, worker, task,
			forward_text=self._worker_count == 1
		)
		try:
			self._run_with_dialog(task, progress)
		except FileNotFoundError:
			# Perhaps the file has already been deleted.
			pass
		except OSError as e:
			with self._alert_lock:
				if self._ignore_errors:
					return True
				text = task.get_title()
				message = 'Error ' + text[0].lower() + text[1:]
				# Windows reports sharing and lock violations as access denied.
				reason = _FILE_IN_USE if (
					getattr(e, 'winerror', None) in _FILE_IN_USE_WINDOWS_ERRORS
					or e.errno == EBUSY
				) else e.strerror or ''
				if not reason and e.errno is not None:
					reason = strerror(e.errno)
				if reason:
					message += ': ' + reason
				message += '.'
				if is_last:
					self.show_alert(message)
				else:
					message += ' Do you want to continue?'
					choice = show_alert(message, YES | NO | YES_TO_ALL)
					if choice & NO:
						return False
					if choice & YES_TO_ALL:
						self._ignore_errors = True
		finally:
			worker.title = ''
		return True
	def _gather_tasks(self):
		for url in self._urls:
			self._prepare(url, self._prepare_fn)
			self._num_urls_prepared += 1
		self.set_size(sum(t.get_size() for t in self._tasks))
	def _prepare(self, url, prepare_fn):
		url_tasks = []
		for task in prepare_fn(url):
			self.check_canceled()
			url_tasks.append(task)
			if task.get_size():
				num = len(self._tasks) + len(url_tasks)
				self.set_text('Preparing to delete {:,} files.'.format(num))
		self._tasks.extend(url_tasks)

def _describe(files, template='%d files'):
	if len(files) == 1:
		return basename(files[0])
	return template % len(files)
