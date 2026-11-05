from core.file_columns import (
	Attributes, Extension, Version, _posix_permissions, _windows_attributes,
)
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace

class _FS:
	def __init__(self, names, folders=(), stats=None):
		self.names, self.folders, self.stats = names, set(folders), stats or {}
	def query(self, url, method):
		if method == 'name':
			return self.names[url]
		if method == 'stat':
			return self.stats[url]
	def is_dir(self, url): return url in self.folders

class FileColumnsTest(TestCase):
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
