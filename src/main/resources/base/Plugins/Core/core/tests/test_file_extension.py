from core.file_extension import (
	name_for_name_column, name_with_hidden_extension, split_extension,
)
from unittest import TestCase
from unittest.mock import patch

class _FS:
	def __init__(self, names, folders=()):
		self.names = names
		self.folders = set(folders)
	def query(self, url, method):
		return self.names[url]
	def is_dir(self, url):
		return url in self.folders

class FileExtensionTest(TestCase):
	def test_split_extension(self):
		cases = [
			('archive.tar.gz', ('archive.tar', 'gz')),
			('report v1.2.txt', ('report v1.2', 'txt')),
			('.gitignore', ('.gitignore', '')),
			('Makefile', ('Makefile', '')),
			('name.', ('name.', '')),
		]
		for name, expected in cases:
			self.assertEqual(expected, split_extension(name))

	def test_name_strips_only_when_enabled_and_extension_column_visible(self):
		fs = _FS({'file': 'report.txt', 'folder': 'folder'}, {'folder'})
		with patch(
			'core.file_extension.shows_name_without_extension', return_value=True,
		):
			self.assertEqual('report', name_for_name_column(fs, 'file'))
			self.assertEqual('folder', name_for_name_column(fs, 'folder'))
		with patch(
			'core.file_extension.shows_name_without_extension', return_value=False,
		):
			self.assertEqual('report.txt', name_for_name_column(fs, 'file'))

	def test_name_with_hidden_extension_restores_suffix_when_active(self):
		fs = _FS({'file': 'report.txt'})
		with patch(
			'core.file_extension.shows_name_without_extension', return_value=True,
		):
			self.assertEqual(
				'report2.txt', name_with_hidden_extension(fs, 'file', 'report2'),
			)
		with patch(
			'core.file_extension.shows_name_without_extension', return_value=False,
		):
			self.assertEqual(
				'report2', name_with_hidden_extension(fs, 'file', 'report2'),
			)
