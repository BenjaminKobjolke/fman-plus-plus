from unittest import TestCase

from fman.impl.util.frozen_path import remove_dirs_below


class RemoveDirsBelowTest(TestCase):
	def test_removes_root_and_subdirectories(self):
		self.assertEqual(
			'C:\\Windows;C:\\app',
			remove_dirs_below(
				'C:\\app\\_internal;C:\\Windows;C:\\app\\_internal\\PyQt5\\Qt5\\bin;C:\\app',
				'C:\\app\\_internal'
			)
		)

	def test_matches_case_insensitively_and_ignores_trailing_backslash(self):
		self.assertEqual(
			'C:\\Windows',
			remove_dirs_below('c:\\APP\\_internal\\;C:\\Windows', 'C:\\app\\_internal')
		)

	def test_keeps_siblings_and_parent(self):
		self.assertEqual(
			'C:\\app\\_internal2;C:\\app',
			remove_dirs_below('C:\\app\\_internal2;C:\\app', 'C:\\app\\_internal')
		)

	def test_empty_path(self):
		self.assertEqual('', remove_dirs_below('', 'C:\\app\\_internal'))
