"""Tests for shortening path titles while preserving useful folders."""

from unittest import TestCase

from fman.impl.path_shortening import ShortenedPath, shorten_path


class ShortenPathTest(TestCase):
	def test_fitting_path_is_returned_unchanged(self):
		path = r'C:\Users\bob\Documents\Projects\fman\src'

		result = shorten_path(path, lambda text: len(text) <= len(path))

		self.assertEqual(ShortenedPath(path, ()), result)

	def test_hides_middle_folders_from_the_left_until_path_fits(self):
		path = r'C:\Users\bob\Documents\Projects\fman\src'

		result = shorten_path(path, lambda text: len(text) <= 19)

		self.assertEqual(r'C:\Users\…\fman\src', result.text)
		self.assertEqual(((9, 31),), result.hidden)

	def test_adjacent_hidden_folders_use_one_ellipsis(self):
		path = r'C:\a\b\c\d\e\f'

		result = shorten_path(path, lambda text: len(text) <= 8)

		self.assertEqual(r'C:\a\…\f', result.text)
		self.assertEqual(1, result.text.count('…'))

	def test_keeps_folder_containing_a_requested_index(self):
		path = r'C:\Users\bob\Documents\Projects\fman\src'

		result = shorten_path(path, lambda text: len(text) <= 24,
			keep=[path.index('Projects') + 1])

		self.assertEqual(r'C:\Users\…\Projects\…\src', result.text)
		self.assertEqual(2, result.text.count('…'))

	def test_preserves_unc_root_and_home_heads(self):
		cases = [
			(r'\\server\share\a\b\c\d', r'\\server\share'),
			('/home/user/a/b/c', '/home'),
			(r'~\Documents\a\b\c', r'~\Documents'),
		]
		for path, head in cases:
			with self.subTest(path=path):
				result = shorten_path(path, lambda _text: False)
				self.assertTrue(result.text.startswith(head))

	def test_returns_none_for_titles_without_enough_path_parts(self):
		for path in ('a/b/c', 'a/very/long folder name'):
			with self.subTest(path=path):
				self.assertIsNone(shorten_path(path, lambda _text: False))

	def test_best_effort_hides_all_hideable_folders_when_none_fit(self):
		path = r'C:\Users\bob\Documents\Projects\fman\src'

		result = shorten_path(path, lambda _text: False)

		self.assertEqual(r'C:\Users\…\src', result.text)

	def test_index_mappings_cover_visible_and_hidden_text(self):
		result = ShortenedPath(r'C:\Users…\src', ((9, 31),))

		self.assertEqual(8, result.shown_index(8))
		self.assertIsNone(result.shown_index(12))
		self.assertEqual(11, result.shown_index(32))
		self.assertEqual(9, result.original_index(9))
		self.assertEqual(31, result.original_index(10))
		self.assertEqual((9, 31), result.hidden_at(9))
		self.assertIsNone(result.hidden_at(8))

	def test_index_mappings_account_for_multiple_hidden_ranges(self):
		result = ShortenedPath('ab…cd…ef', ((2, 5), (8, 11)))

		self.assertEqual(0, result.shown_index(0))
		self.assertEqual(3, result.shown_index(5))
		self.assertIsNone(result.shown_index(9))
		self.assertEqual(8, result.shown_index(12))
		self.assertEqual(12, result.original_index(8))
		self.assertEqual((8, 11), result.hidden_at(6))

