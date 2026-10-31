from core.util import format_size, is_relative_name, strformat_dict_values
from unittest import TestCase
from unittest.mock import patch

import os

class TestStrformatDictValues(TestCase):
	def test_empty(self):
		self.assertEqual({}, strformat_dict_values({}, {'a': 'b'}))
	def test_simple_replacement(self):
		self.assertEqual(
			{'a': 'a was replaced', 'c': 'd'},
			strformat_dict_values(
				{'a': '{a}', 'c': 'd'},
				{'a': 'a was replaced'}
			)
		)
	def test_list(self):
		self.assertEqual(
			{'list': ['replaced']},
			strformat_dict_values(
				{'list': ['{replaceme}']},
				{'replaceme': 'replaced'}
			)
		)
	def test_list_ints(self):
		dict_ = {'list': [1]}
		self.assertEqual(dict_, strformat_dict_values(dict_, {'a': 'b'}))

class TestFormatSize(TestCase):
	def test_formats_existing_units(self):
		for size, expected in (
			(0, '0 B'),
			(512, '512 B'),
			(2 * 1024, '2 KB'),
			(int(1.5 * 1024 ** 2), '1.5 MB'),
			(int(3.2 * 1024 ** 3), '3.2 GB'),
		):
			with self.subTest(size=size):
				self.assertEqual(expected, format_size(size))

	def test_formats_terabytes(self):
		self.assertEqual('4.0 TB', format_size(4 * 1024 ** 4))

class TestIsRelativeName(TestCase):
	def test_rejects_path_separators_and_dot_names(self):
		for name in ('folder' + os.sep + 'file', '.', '..'):
			with self.subTest(name=name):
				self.assertFalse(is_relative_name(name))

	def test_accepts_plain_file_names(self):
		for name in ('report.txt', 'a-b', 'name with spaces'):
			with self.subTest(name=name):
				self.assertTrue(is_relative_name(name))

	@patch('core.util.PLATFORM', 'Windows')
	def test_rejects_forward_slashes_on_windows(self):
		self.assertFalse(is_relative_name('folder/file.txt'))
