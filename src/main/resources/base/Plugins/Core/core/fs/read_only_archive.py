"""Shared read-only behavior for archive filesystems backed by 7-Zip."""

from core.fs.zip import _7ZipFileSystem
from fman import Task
from fman.url import basename, splitscheme
from io import UnsupportedOperation


class _ReadOnly7ZipFileSystem(_7ZipFileSystem):
	read_only_message = None

	def prepare_copy(self, src_url, dst_url):
		if splitscheme(dst_url)[0] == self.scheme:
			return [Task(
				'Copying ' + basename(src_url), fn=self._refuse_write
			)]
		return super().prepare_copy(src_url, dst_url)

	def prepare_move(self, src_url, dst_url):
		if (splitscheme(src_url)[0] == self.scheme or
				splitscheme(dst_url)[0] == self.scheme):
			return [Task(
				'Moving ' + basename(src_url), fn=self._refuse_write
			)]
		return super().prepare_move(src_url, dst_url)

	def mkdir(self, path):
		self._refuse_write()

	def delete(self, path):
		self._refuse_write()

	def prepare_delete(self, path):
		raise UnsupportedOperation()

	def _refuse_write(self):
		raise PermissionError(self.read_only_message)


__all__ = []
