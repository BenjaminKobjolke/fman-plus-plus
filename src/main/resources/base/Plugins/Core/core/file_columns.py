"""Additional columns for filesystems backed by file metadata."""
from core import Name
from core.column_visibility import is_column_hidden
from core.file_extension import split_extension
from core.overwrite_details import file_version
from fman import PLATFORM
from fman.fs import Column
from core.mixed_sort import DirsFirstColumn
import stat
import fman.fs

class Extension(DirsFirstColumn, Column):
	def __init__(self, fs=fman.fs):
		super().__init__()
		self._fs = fs
	def get_str(self, url):
		try:
			if self._fs.is_dir(url):
				return ''
			return split_extension(self._fs.query(url, 'name'))[1]
		except OSError:
			return ''
	def get_sort_value(self, url, is_ascending):
		try:
			is_dir = self._fs.is_dir(url)
		except OSError:
			is_dir = False
		extension = self.get_str(url).lower()
		name_sort = Name(self._fs).get_sort_value(url, is_ascending)[1]
		return is_dir ^ is_ascending, extension, name_sort

class Version(DirsFirstColumn, Column):
	def __init__(self, fs=fman.fs):
		super().__init__()
		self._fs = fs
	def get_str(self, url):
		if is_column_hidden('core.file_columns.Version'):
			return ''
		return file_version(url)
	def get_sort_value(self, url, is_ascending):
		try:
			is_dir = self._fs.is_dir(url)
		except OSError:
			is_dir = False
		try:
			version = tuple(int(part) for part in self.get_str(url).split('.'))
		except ValueError:
			version = ()
		return is_dir ^ is_ascending, version

class Attributes(DirsFirstColumn, Column):
	def __init__(self, fs=fman.fs):
		super().__init__()
		self._fs = fs
	def get_str(self, url):
		try:
			metadata = self._fs.query(url, 'stat')
			if PLATFORM == 'Windows':
				return _windows_attributes(metadata.st_file_attributes)
			return _posix_permissions(metadata.st_mode)
		except OSError:
			return ''
	def get_sort_value(self, url, is_ascending):
		try:
			is_dir = self._fs.is_dir(url)
		except OSError:
			is_dir = False
		return is_dir ^ is_ascending, self.get_str(url)

def _windows_attributes(attributes):
	flags = (
		('r', getattr(stat, 'FILE_ATTRIBUTE_READONLY', 1)),
		('h', getattr(stat, 'FILE_ATTRIBUTE_HIDDEN', 2)),
		('s', getattr(stat, 'FILE_ATTRIBUTE_SYSTEM', 4)),
		('a', getattr(stat, 'FILE_ATTRIBUTE_ARCHIVE', 32)),
	)
	return ''.join(letter if attributes & mask else '-' for letter, mask in flags)

def _posix_permissions(mode):
	return stat.filemode(mode)[1:]
