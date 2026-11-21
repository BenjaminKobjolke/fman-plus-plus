from core.file_columns import (
	Attributes, Comment, Created, Extension, Version, _posix_permissions,
	_windows_attributes,
)
from datetime import datetime
from fman.url import as_url
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import patch
from types import SimpleNamespace
import os

class _FS:
	def __init__(self, names, folders=(), stats=None, created=None, modified=None):
		self.names, self.folders, self.stats = names, set(folders), stats or {}
		self.created, self.modified = created or {}, modified or {}
	def query(self, url, method):
		if method == 'name':
			return self.names[url]
		if method == 'stat':
			return self.stats[url]
		if method == 'created_datetime':
			return self.created.get(url)
		if method == 'modified_datetime':
			return self.modified.get(url)
	def is_dir(self, url): return url in self.folders

class FileColumnsTest(TestCase):
	def test_comment_text_and_sorting(self):
		fs = _FS({'folder':'folder', 'a':'a', 'b':'b'}, {'folder'})
		column = Comment(fs)
		with patch('core.file_columns.get_comment', side_effect={
			'folder':'Zulu note\nsecond line', 'a':'Alpha note', 'b':'beta note',
		}.get):
			self.assertEqual('Zulu note', column.get_str('folder'))
			self.assertLess(
				column.get_sort_value('folder', True),
				column.get_sort_value('a', True),
			)
			self.assertLess(
				column.get_sort_value('a', True), column.get_sort_value('b', True),
			)
			self.assertEqual(
				column.get_sort_value('folder', True)[1:],
				column.get_mixed_sort_value('folder', True),
			)

	def test_comment_returns_empty_when_read_fails(self):
		with patch('core.file_columns.get_comment', side_effect=OSError):
			self.assertEqual('', Comment().get_str('file:///missing'))

	def test_local_default_columns_include_comment_last(self):
		from core.fs.local import LocalFileSystem
		columns = LocalFileSystem().get_default_columns('file:///')
		self.assertEqual('core.file_columns.Comment', columns[-1])
		self.assertEqual(
			'core.file_columns.Created', columns[columns.index('core.Modified') + 1],
		)

	@skipUnless(
		hasattr(os.stat(__file__), 'st_birthtime'),
		'This platform does not expose st_birthtime',
	)
	def test_local_created_datetime_uses_birthtime(self):
		from core.fs.local import LocalFileSystem
		with TemporaryDirectory() as directory:
			path = Path(directory, 'created.txt')
			path.touch()
			self.assertEqual(
				datetime.fromtimestamp(os.stat(path).st_birthtime),
				LocalFileSystem().created_datetime(
					as_url(str(path))[len('file://'):]
				),
			)

	def test_local_created_datetime_is_none_without_birthtime(self):
		from core.fs.local import LocalFileSystem
		with patch.object(
			LocalFileSystem, 'stat', return_value=SimpleNamespace(st_mtime=1.0)
		):
			self.assertIsNone(LocalFileSystem().created_datetime('file:///path'))

	def test_extension_text_and_sorting(self):
		fs = _FS({'b':'B.txt', 'a':'a.TXT', 'folder':'folder'}, {'folder'})
		column = Extension(fs)
		self.assertEqual('TXT', column.get_str('a'))
		self.assertEqual('', column.get_str('folder'))
		self.assertLess(
			column.get_sort_value('folder', True), column.get_sort_value('a', True),
		)
		self.assertLess(
			column.get_sort_value('a', True), column.get_sort_value('b', True),
		)
		self.assertEqual(
			column.get_sort_value('folder', True)[1:],
			column.get_mixed_sort_value('folder', True)
		)

	def test_version_empty_while_hidden_and_numeric_sort(self):
		with patch('core.file_columns.is_column_hidden', return_value=True):
			self.assertEqual('', Version().get_str('file:///app.exe'))
		fs = _FS({'nine':'9.exe', 'ten':'10.exe'})
		column = Version(fs)
		with patch('core.file_columns.is_column_hidden', return_value=False), patch(
			'core.file_columns.file_version', side_effect=['9.1', '10.0']
		):
			self.assertLess(
				column.get_sort_value('nine', True), column.get_sort_value('ten', True),
			)

	def test_attribute_formatters(self):
		self.assertEqual('-h-a', _windows_attributes(2 | 32))
		self.assertEqual('rwxr-xr-x', _posix_permissions(0o100755))

class AttributeColumnTest(TestCase):
	def test_attributes_read_the_platform_stat(self):
		fs = _FS(
			{'f': 'f'},
			stats={'f': SimpleNamespace(st_mode=0o100755, st_file_attributes=0)},
		)
		with patch('core.file_columns.PLATFORM', 'Linux'):
			self.assertEqual('rwxr-xr-x', Attributes(fs).get_str('f'))

class CreatedColumnTest(TestCase):
	def test_created_formats_like_modified(self):
		created = datetime(2024, 1, 2, 3, 4, 5)
		created_column = Created(_FS({'file': 'file'}, created={'file': created}))
		from core import Modified
		modified_column = Modified(
			_FS({'file': 'file'}, modified={'file': created})
		)
		self.assertEqual(
			modified_column.get_str('file'), created_column.get_str('file')
		)

	def test_created_empty_and_sorting(self):
		from core import Modified
		fs = _FS(
			{'folder': 'folder', 'older': 'older', 'newer': 'newer'},
			{'folder'},
			created={
				'older': datetime(2024, 1, 1),
				'newer': datetime(2024, 1, 2),
			},
		)
		column = Created(fs)
		self.assertEqual('', column.get_str('missing-date'))
		self.assertLess(
			column.get_sort_value('folder', True),
			column.get_sort_value('older', True),
		)
		self.assertLess(
			column.get_sort_value('older', True),
			column.get_sort_value('newer', True),
		)

	def test_created_handles_filesystem_without_creation_time(self):
		class _FSWithoutCreated(_FS):
			def query(self, url, method):
				if method == 'created_datetime':
					raise AttributeError(method)
				return super().query(url, method)
		column = Created(_FSWithoutCreated({'file': 'file'}))
		self.assertEqual('', column.get_str('file'))
		self.assertIsNotNone(column.get_sort_value('file', True))
