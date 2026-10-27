from core.trash import move_to_trash
from core.util import filenotfounderror
from datetime import datetime
from errno import ENOENT
from fman import PLATFORM, Task
from fman.fs import FileSystem, cached
from fman.impl.util.qt.thread import run_in_main_thread
from fman.url import as_url, splitscheme, as_human_readable
from os import remove, rmdir
from os.path import islink, samestat, isabs, splitdrive
from pathlib import Path
from PyQt5.QtCore import QFileSystemWatcher
from stat import S_ISDIR, S_IWRITE
from core.fs.local.transfers import (
	CopyFile as CopyFile, DeleteIfEmpty as DeleteIfEmpty, LocalTransfers,
	MoveByCopying as MoveByCopying,
)

import errno
import os

if PLATFORM == 'Windows':
	from core.fs.local.windows.drives import (
		DrivesFileSystem as DrivesFileSystem, DriveName as DriveName,
		DriveSize as DriveSize, DriveFree as DriveFree
	)
	from core.fs.local.windows.network import NetworkFileSystem as NetworkFileSystem

class LocalFileSystem(LocalTransfers, FileSystem):

	scheme = 'file://'

	def __init__(self):
		super().__init__()
		self._watcher = None
	def get_default_columns(self, path):
		return 'core.Name', 'core.Size', 'core.Modified'
	def exists(self, path):
		os_path = self._url_to_os_path(path)
		return self._isabs(os_path) and Path(os_path).exists()
	def iterdir(self, path):
		os_path = self._url_to_os_path(path)
		if not self._isabs(os_path):
			raise filenotfounderror(path)
		# Use os.listdir(...) instead of Path(...).iterdir() for performance:
		return os.listdir(os_path)
	def is_dir(self, existing_path):
		# Like Python's isdir(...) except raises FileNotFoundError if the file
		# does not exist and OSError if there is another error.
		return S_ISDIR(self.stat(existing_path).st_mode)
	@cached
	def stat(self, path):
		os_path = self._url_to_os_path(path)
		if not self._isabs(os_path):
			raise filenotfounderror(path)
		try:
			return os.stat(os_path)
		except FileNotFoundError:
			return os.stat(os_path, follow_symlinks=False)
	def size_bytes(self, path):
		return self.stat(path).st_size
	def modified_datetime(self, path):
		return datetime.fromtimestamp(self.stat(path).st_mtime)
	def touch(self, path):
		os_path = Path(self._url_to_os_path(path))
		if not os_path.is_absolute():
			raise ValueError('Path must be absolute')
		try:
			os_path.touch(exist_ok=False)
		except FileExistsError:
			os_path.touch(exist_ok=True)
		else:
			self.notify_file_added(path)
	def makedirs(self, path, exist_ok=True):
		# Otherwise the base recursion reaches a bare drive or server name.
		drive = splitdrive(self._url_to_os_path(path))[0]
		if drive and not os.path.isdir(drive + '\\'):
			raise FileNotFoundError(
				ENOENT, 'The drive or network share is not available', drive
			)
		super().makedirs(path, exist_ok)
	def mkdir(self, path):
		os_path = Path(self._url_to_os_path(path))
		if not os_path.is_absolute():
			raise ValueError('Path must be absolute')
		try:
			os_path.mkdir()
		except FileNotFoundError:
			raise
		except IsADirectoryError: # macOS
			raise FileExistsError(path)
		except OSError as e:
			if e.errno == ENOENT:
				raise filenotfounderror(path) from e
			elif os_path.exists():
				# On at least Windows, Path('Z:\\').mkdir() raises
				# PermissionError instead of FileExistsError. We want the latter
				# however because #makedirs(...) relies on it. So handle this
				# case generally here:
				raise FileExistsError(path) from e
			else:
				raise
		self.notify_file_added(path)
	def move_to_trash(self, path):
		for task in self.prepare_trash(path):
			task()
	def prepare_trash(self, path):
		os_path = self._url_to_os_path(path)
		if not self._isabs(os_path):
			raise filenotfounderror(path)
		yield Task(
			'Deleting ' + path.rsplit('/', 1)[-1], size=1,
			fn=self._do_trash, args=(path, os_path)
		)
	def _do_trash(self, path, os_path):
		move_to_trash(os_path)
		self.notify_file_removed(path)
	def delete(self, path):
		for task in self.prepare_delete(path):
			task()
	def prepare_delete(self, path):
		os_path = self._url_to_os_path(path)
		if not self._isabs(os_path):
			raise filenotfounderror(path)
		# is_dir(...) follows symlinks. But if `path` is a symlink, we need to
		# use remove(...) instead of rmdir(...) to avoid NotADirectoryError.
		# So check if `path` is a symlink:
		if self.is_dir(path) and not islink(os_path):
			for name in self.iterdir(path):
				try:
					yield from self.prepare_delete(path + '/' + name)
				except FileNotFoundError:
					pass
			delete_fn = rmdir
		else:
			delete_fn = remove
		yield Task(
			'Deleting ' + path.rsplit('/', 1)[-1], size=1,
			fn=self._do_delete, args=(path, delete_fn)
		)
	def _do_delete(self, path, delete_fn):
		os_path = self._url_to_os_path(path)
		try:
			delete_fn(os_path)
		except OSError as orig_exc:
			try:
				mode = self.stat(path).st_mode
			except OSError:
				mode = 0
			if not (mode & S_IWRITE):
				try:
					Path(os_path).chmod(mode | S_IWRITE)
				except OSError:
					raise orig_exc
				# Try again, now the file is writeable:
				delete_fn(os_path)
		self.notify_file_removed(path)
	def resolve(self, path):
		path = self._url_to_os_path(path)
		if not self._isabs(path):
			raise filenotfounderror(path)
		if PLATFORM == 'Windows':
			is_unc_server = path.startswith(r'\\') and '\\' not in path[2:]
			if is_unc_server:
				# Python can handle \\server\folder but not \\server. Defer to
				# the network:// file system.
				return 'network://' + path[2:]
		p = Path(path)
		try:
			path = p.resolve(strict=True)
		except FileNotFoundError:
			if not p.exists():
				raise
		except OSError as e:
			# We for instance get errno.EINVAL ("[WinError 1]") when trying to
			# resolve folders on Cryptomator drives on Windows. Ignore it:
			if e.errno != errno.EINVAL:
				raise
		return as_url(path)
	def samefile(self, path1, path2):
		s1 = self.stat(path1)
		s2 = self.stat(path2)
		if s1.st_ino and s1.st_dev:
			return samestat(s1, s2)
		# samestat(...) above simply compares .st_ino and .st_dev.
		# However, there are cases where both of these values are 0.
		# This for instance happens on Windows Google Drive File Stream folders.
		# Fall back to comparing the (resolved) path to give meaningful results:
		return self.resolve(path1) == self.resolve(path2)
	@run_in_main_thread
	def watch(self, path):
		self._get_watcher().addPath(self._url_to_os_path(path))
	@run_in_main_thread
	def unwatch(self, path):
		self._get_watcher().removePath(self._url_to_os_path(path))
	def _get_watcher(self):
		# Instantiate QFileSystemWatcher as late as possible. It requires a
		# QApplication which isn't available in some tests.
		if self._watcher is None:
			if PLATFORM == 'Windows':
				# On Windows, QFileSystemWatcher keeps excessive locks on files
				# and directories. This sometimes makes it impossible for fman
				# or other apps to access them properly. One example of this are
				# USB drives that can't be ejected as long as fman is running.
				# So don't watch files on Windows for now, perhaps until we have
				# a better implementation.
				self._watcher = StubFileSystemWatcher()
			else:
				self._watcher = QFileSystemWatcher()
				self._watcher.directoryChanged.connect(self._on_file_changed)
				self._watcher.fileChanged.connect(self._on_file_changed)
		return self._watcher
	def _on_file_changed(self, file_path):
		path_forward_slashes = splitscheme(as_url(file_path))[1]
		self.notify_file_changed(path_forward_slashes)
	def _url_to_os_path(self, path):
		# Convert a "URL path" a/b to a path understood by the OS, eg. a\b on
		# Windows. An important effect of this function is that it turns
		# C: -> C:\. This is required for Python functions such as Path#resolve.
		return as_human_readable(self.scheme + path)
	def _isabs(self, os_path):
		# Python's isabs(...) says \\host\share is *not* absolute. But for our
		# purposes, it is. So add some extra logic to handle this case:
		return isabs(os_path) or splitdrive(os_path)[0]


class StubFileSystemWatcher:
	def addPath(self, path):
		pass
	def removePath(self, path):
		pass
