"""Local filesystem transfer operations and their executable tasks."""

import errno
import os
from pathlib import Path
from shutil import copystat
from os import remove, rmdir
from os.path import islink
from io import UnsupportedOperation

from fman import Task
from fman.url import (
	as_human_readable, basename, dirname, join, splitscheme,
)

from core.fs.local import locks


class LocalTransfers:
	def move(self, src_url, dst_url):
		self._check_transfer_precnds(src_url, dst_url)
		for task in self._prepare_move(src_url, dst_url):
			task()
	def prepare_move(self, src_url, dst_url):
		self._check_transfer_precnds(src_url, dst_url)
		return self._prepare_move(src_url, dst_url, measure_size=True)
	def _prepare_move(
		self, src_url, dst_url, measure_size=False, use_rename=True,
		expected_st_dev=None
	):
		if expected_st_dev is None:
			expected_st_dev = {}
		src_path, dst_path = self._check_transfer_precnds(src_url, dst_url)
		if use_rename:
			src_stat = self.stat(src_path)
			dst_par_path = splitscheme(dirname(dst_url))[1]
			try:
				dst_par_dev = expected_st_dev[dst_par_path]
			except KeyError:
				dst_par_dev = self.stat(dst_par_path).st_dev
			if src_stat.st_dev == dst_par_dev:
				task = Task(
					'Moving ' + basename(src_url), size=1,
					fn=self._rename, args=(src_url, dst_url)
				)
				# Core reads this attribute; plugin filesystems can opt in too.
				task.moved_urls = (src_url, dst_url)
				yield task
				return
		src_is_dir = self.is_dir(src_path)
		if src_is_dir:
			yield Task(
				'Creating ' + basename(dst_url), fn=self.mkdir, args=(dst_path,)
			)
			dst_par_path = splitscheme(dirname(dst_url))[1]
			# Expect `dst_path` to inherit .st_dev from its parent:
			try:
				expected_st_dev[dst_path] = expected_st_dev[dst_par_path]
			except KeyError:
				expected_st_dev[dst_path] = self.stat(dst_par_path).st_dev
			for name in self.iterdir(src_path):
				try:
					yield from self._prepare_move(
						join(src_url, name), join(dst_url, name), measure_size,
						use_rename, expected_st_dev
					)
				except FileNotFoundError:
					pass
			yield DeleteIfEmpty(self, src_url)
		else:
			size = self.size_bytes(src_path) if measure_size else 0
			# It's tempting to "yield copy" then "yield delete" here. But this
			# can lead to data loss: fman / the user may choose to ignore errors
			# in a particular subtask. (Eg. moving file1.txt failed but the user
			# wants to go on to move file2.txt.) If we ignored a failure in
			# "yield copy" but then execute the "yield delete", we would delete
			# a file that has not been copied!
			# To avoid this, we "copy and delete" as a single, atomic task:
			yield MoveByCopying(self, src_url, dst_url, size)
	def _rename(self, src_url, dst_url):
		src_path = splitscheme(src_url)[1]
		os_src_path = self._url_to_os_path(src_path)
		dst_path = splitscheme(dst_url)[1]
		os_dst_path = self._url_to_os_path(dst_path)
		Path(os_src_path).replace(os_dst_path)
		self.notify_file_removed(src_path)
		self.notify_file_added(dst_path)
	def copy(self, src_url, dst_url):
		self._check_transfer_precnds(src_url, dst_url)
		for task in self._prepare_copy(src_url, dst_url):
			task()
	def prepare_copy(self, src_url, dst_url):
		self._check_transfer_precnds(src_url, dst_url)
		return self._prepare_copy(src_url, dst_url, measure_size=True)
	def _prepare_copy(self, src_url, dst_url, measure_size=False):
		src_path, dst_path = self._check_transfer_precnds(src_url, dst_url)
		src_is_dir = self.is_dir(src_path)
		if src_is_dir:
			yield Task(
				'Creating ' + basename(dst_url), fn=self.mkdir, args=(dst_path,)
			)
			for name in self.iterdir(src_path):
				try:
					yield from self._prepare_copy(
						join(src_url, name), join(dst_url, name), measure_size
					)
				except FileNotFoundError:
					pass
		else:
			size = self.size_bytes(src_path) if measure_size else 0
			yield CopyFile(self, src_url, dst_url, size)
	def _check_transfer_precnds(self, src_url, dst_url):
		src_scheme, src_path = splitscheme(src_url)
		dst_scheme, dst_path = splitscheme(dst_url)
		if src_scheme != self.scheme or dst_scheme != self.scheme:
			raise UnsupportedOperation(
				"%s only supports transferring to and from %s." %
				(self.__class__.__name__, self.scheme)
			)
		if not self._isabs(self._url_to_os_path(dst_path)):
			raise ValueError('Destination path must be absolute')
		return src_path, dst_path


class CopyFile(Task):
	def __init__(self, fs, src_url, dst_url, size_bytes):
		super().__init__('Copying ' + basename(src_url), size=size_bytes)
		self._fs = fs
		self._src_url = src_url
		self._dst_url = dst_url
	def __call__(self):
		dst_urlpath = splitscheme(self._dst_url)[1]
		dst_existed = self._fs.exists(dst_urlpath)
		src = as_human_readable(self._src_url)
		dst = as_human_readable(self._dst_url)
		if islink(src):
			os.symlink(os.readlink(src), dst)
			copystat(src, dst, follow_symlinks=False)
		else:
			if dst_existed:
				locks.raise_if_locked(dst)
			temp = dst + '.fman-partial'
			try:
				with open(src, 'rb') as fsrc:
					with open(temp, 'wb') as fdst:
						num_written = 0
						while True:
							self.check_canceled()
							buf = fsrc.read(16 * 1024)
							if not buf:
								break
							num_written += fdst.write(buf)
							self.set_progress(num_written)
				copystat(src, temp, follow_symlinks=False)
				os.replace(temp, dst)
			except BaseException:
				try:
					remove(temp)
				except FileNotFoundError:
					pass
				raise
		if not dst_existed:
			self._fs.notify_file_added(dst_urlpath)


class MoveByCopying(Task):
	def __init__(self, fs, src_url, dst_url, size_bytes):
		super().__init__('Moving ' + basename(src_url), size=size_bytes)
		self._fs = fs
		self._src_url = src_url
		self._dst_url = dst_url
		# Core reads this attribute; plugin filesystems can opt in too.
		self.moved_urls = (src_url, dst_url)
	def __call__(self, *args, **kwargs):
		locks.raise_if_locked(as_human_readable(self._src_url))
		self._fs.copy(self._src_url, self._dst_url)
		self._fs.delete(splitscheme(self._src_url)[1])


class DeleteIfEmpty(Task):
	def __init__(self, fs, dir_url):
		super().__init__('Deleting ' + basename(dir_url), size=1)
		self._fs = fs
		self._dir_url = dir_url
	def __call__(self, *args, **kwargs):
		try:
			rmdir(as_human_readable(self._dir_url))
		except FileNotFoundError:
			pass
		except OSError as e:
			if e.errno != errno.ENOTEMPTY:
				raise
		else:
			self._fs.notify_file_removed(splitscheme(self._dir_url)[1])
