from core.path_completion import complete_path
from unittest import TestCase

import os


class PathCompletionTest(TestCase):
	class FileSystem:
		def __init__(self, entries=(), listing_error=None, dir_errors=()):
			self.entries = entries
			self.listing_error = listing_error
			self.dir_errors = set(dir_errors)
			self.listed = None

		def iterdir(self, url):
			self.listed = url
			if self.listing_error:
				raise self.listing_error
			return [name for name, _ in self.entries]

		def is_dir(self, url):
			name = url.rsplit('/', 1)[-1]
			if name in self.dir_errors:
				raise OSError(name)
			return dict(self.entries)[name]

	def test_relative_partial_matches_folders_case_insensitively(self):
		fs = self._fs(('proj', True), ('Programs', True), ('profile.txt', False))
		self.assertEqual(
			['Programs' + os.sep, 'proj' + os.sep],
			complete_path('pro', 'file://C:/dest', fs=fs)
		)
		self.assertEqual('file://C:/dest', fs.listed.rstrip('/'))

	def test_absolute_windows_path_preserves_typed_prefix(self):
		fs = self._fs(('proj', True))
		self.assertEqual(
			['C:\\dest\\proj' + os.sep],
			complete_path('C:\\dest\\pr', 'file://C:/other', fs=fs)
		)

	def test_empty_partial_lists_all_folders(self):
		fs = self._fs(('a', True), ('file.txt', False), ('b', True))
		self.assertEqual(
			['sub' + os.sep + 'a' + os.sep,
			 'sub' + os.sep + 'b' + os.sep],
			complete_path('sub' + os.sep, 'file://C:/dest', fs=fs)
		)

	def test_url_uses_url_separator_and_keeps_scheme(self):
		fs = self._fs(('alpha', True), ('archive', False))
		self.assertEqual(
			['ftp://host/dir/alpha/'],
			complete_path('ftp://host/dir/a', 'ftp://host/dir', fs=fs)
		)
		self.assertEqual('ftp://host/dir/', fs.listed)

	def test_relative_path_can_be_based_on_source_directory(self):
		fs = self._fs(('archive', True))
		self.assertEqual(
			['archive' + os.sep],
			complete_path('ar', 'file://C:/dest', 'file://C:/source', fs)
		)
		self.assertEqual('file://C:/source', fs.listed.rstrip('/'))

	def test_listing_oserror_returns_no_completions(self):
		for error in (FileNotFoundError(), OSError()):
			with self.subTest(error=type(error).__name__):
				fs = self._fs(listing_error=error)
				self.assertEqual([], complete_path('a', 'file://C:/dest', fs=fs))

	def test_entry_oserror_skips_only_that_folder(self):
		fs = self._fs(('alpha', True), ('another', True), dir_errors=('alpha',))
		self.assertEqual(
			['another' + os.sep],
			complete_path('a', 'file://C:/dest', fs=fs)
		)

	def _fs(self, *entries, listing_error=None, dir_errors=()):
		return self.FileSystem(entries, listing_error, dir_errors)
