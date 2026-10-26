"""Track completed moves so Core can safely undo a stopped transfer."""

from threading import Lock
from fman.url import as_human_readable, dirname, join, splitscheme

import errno
import os


class MoveRollback:

	def __init__(self):
		self._moves = []
		self._new_destinations = set()
		self._lock = Lock()

	def record(self, task):
		moved_urls = getattr(task, 'moved_urls', None)
		if moved_urls is None:
			return
		with self._lock:
			self._moves.append(moved_urls)

	def add_new_destination(self, url):
		with self._lock:
			self._new_destinations.add(url)

	def run(self, fs):
		with self._lock:
			moves = list(reversed(self._moves))
			self._moves.clear()
			new_destinations = sorted(
				self._new_destinations, key=lambda url: url.count('/'),
				reverse=True
			)
			self._new_destinations.clear()
		failed_urls = []
		for source_url, destination_url in moves:
			try:
				source_path = _path_for_fs(fs, source_url)
				if fs.exists(source_path):
					failed_urls.append(destination_url)
					continue
				fs.makedirs(_path_for_fs(fs, dirname(source_url)))
				fs.move(destination_url, source_url)
			except OSError:
				failed_urls.append(destination_url)
		for destination_url in new_destinations:
			_remove_empty_directories(fs, destination_url, failed_urls)
		return failed_urls


def _remove_empty_directories(fs, url, failed_urls):
	path = _path_for_fs(fs, url)
	os_path = as_human_readable(url)
	if os.path.islink(os_path):
		return
	try:
		if not fs.is_dir(path):
			return
		for name in fs.iterdir(path):
			_remove_empty_directories(fs, join(url, name), failed_urls)
		# rmdir is atomic with respect to the empty check; recursive delete could
		# remove a file another process added after the directory was inspected.
		os.rmdir(os_path)
	except FileNotFoundError:
		return
	except OSError as error:
		if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
			failed_urls.append(url)
	else:
		fs.notify_file_removed(path)


def _path_for_fs(fs, url):
	return splitscheme(url)[1] if getattr(fs, 'scheme', None) else url
