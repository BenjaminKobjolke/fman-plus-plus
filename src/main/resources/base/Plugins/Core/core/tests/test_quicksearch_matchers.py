from core.quicksearch_matchers import basename_contains_chars, \
	bucket_count, contains_chars, contains_chars_after_separator, \
	contains_chars_any_order, contains_words, match_titles_or_keywords
from unittest import TestCase

class ContainsCharsAfterSeparatorTest(TestCase):
	def test_simple(self):
		self.assertEqual(
			[0, 5], self.find_chars_after_space('copy paths', 'cp')
		)
	def test_chars_in_first_and_second_part(self):
		self.assertEqual(
			[0, 1, 2], self.find_chars_after_space('copy paths', 'cop')
		)
	def test_no_match(self):
		self.assertIsNone(self.find_chars_after_space('copy paths', 'cd'))
	def test_full_word_match(self):
		self.assertEqual(
			[0, 1, 2, 3, 5],
			self.find_chars_after_space('copy paths', 'copyp')
		)
	def test_prefix_match(self):
		self.assertEqual(
			[0, 1],
			self.find_chars_after_space('column count', 'co')
		)
	def setUp(self):
		super().setUp()
		self.find_chars_after_space = contains_chars_after_separator(' ')

class ContainsCharsAnyOrderTest(TestCase):
	def test_reversed_order_matches(self):
		result = contains_chars_any_order('show all panes', 'panes show')
		self.assertIsNotNone(result)
		# Highlights both the 'show' and 'panes' words:
		self.assertEqual([0, 1, 2, 3, 9, 10, 11, 12, 13], result)
	def test_in_order_matches(self):
		self.assertIsNotNone(
			contains_chars_any_order('show all panes', 'show panes')
		)
	def test_missing_word_is_no_match(self):
		self.assertIsNone(
			contains_chars_any_order('show all panes', 'panes missing')
		)
	def test_empty_query_is_no_match(self):
		self.assertIsNone(contains_chars_any_order('show all panes', ''))

class ContainsWordsTest(TestCase):
	def test_words_match_in_any_order(self):
		self.assertEqual(
			[0, 1, 2, 8, 9, 10], contains_words('ryd/inv.pdf', 'pdf ryd')
		)
	def test_scattered_letters_are_no_match(self):
		self.assertIsNone(contains_words('cip_ jfa_reality_webpage', 'pdf ryd'))
	def test_empty_query_is_no_match(self):
		self.assertIsNone(contains_words('abc', ' '))

class BasenameContainsCharsTest(TestCase):
	def test_letters_are_found_in_the_name_with_path_offsets(self):
		self.assertEqual(
			[6, 8], basename_contains_chars('tools/mod_x.py', 'md')
		)
	def test_letters_in_the_folders_do_not_count(self):
		self.assertIsNone(basename_contains_chars('pdf/webpage', 'pdf'))
	def test_several_words_are_no_loose_match(self):
		name = '2026_10_05_streifen.sync-conflict-20261104-esybydw.pdf'
		self.assertIsNone(basename_contains_chars(name, 'ryd pdf 2026 11 16'))
class MatchTitlesOrKeywordsTest(TestCase):

	# The two cheapest of the palette's matchers; the third (any order) adds
	# nothing to what this helper does with them.
	_MATCHERS = (contains_chars_after_separator(' '), contains_chars)

	def test_exact_title_is_the_top_bucket(self):
		self.assertEqual(
			(0, 0, [0, 1, 2, 3]), self._match(['quit'], [], 'quit')
		)
	def test_exact_keyword_outranks_a_loose_title_match(self):
		# What made typing 'exit' offer Extract to opposite before Quit:
		# 'exit' is a mid-word subsequence of the former's name, but the
		# whole of the latter's hidden keyword.
		by_keyword = self._match(['quit'], ['exit'], 'exit')
		by_loose_title = self._match(['extract to opposite'], [], 'exit')
		self.assertEqual(0, by_keyword[0])
		self.assertLess(by_keyword[0], by_loose_title[0])
	def test_exact_title_and_exact_keyword_share_the_top_bucket(self):
		# Neither wins on rank; the palette's own title sort separates them.
		by_title = self._match(['reload'], [], 'reload')
		by_keyword = self._match(['set window opacity'], ['reload'], 'reload')
		self.assertEqual(0, by_title[0])
		self.assertEqual(0, by_keyword[0])
	def test_title_match_keeps_its_bucket_and_highlight(self):
		self.assertEqual(
			(1, 0, [0, 4, 11]),
			self._match(['set window opacity'], [], 'swo')
		)
	def test_falls_through_to_the_next_matcher(self):
		self.assertEqual(
			(2, 0, [8, 14, 16]),
			self._match(['set window opacity'], [], 'oct')
		)
	def test_first_matching_title_wins(self):
		# Declaration order decides which of a command's names titles the row,
		# the way the palette's alias loop always has.
		self.assertEqual(
			(1, 0, [0, 1, 2]), self._match(['view file', 'view'], [], 'vie')
		)
	def test_an_exact_name_titles_the_row_even_if_declared_later(self):
		self.assertEqual(
			(0, 1, [0, 1, 2, 3]),
			self._match(['view file', 'view'], [], 'view')
		)
	def test_keyword_only_match_uses_first_title_without_highlight(self):
		self.assertEqual(
			(bucket_count(self._MATCHERS) - 1, 0, []),
			self._match(['set window opacity'], ['transparency'], 'transp')
		)
	def test_title_match_outranks_loose_keyword_match(self):
		by_title = self._match(['zoom in'], [], 'zoom')
		by_keyword = self._match(['increase font size'], ['zoom in out'], 'zoom')
		self.assertLess(by_title[0], by_keyword[0])
	def test_no_match_anywhere(self):
		self.assertIsNone(
			self._match(['set window opacity'], ['transparency'], 'xyz')
		)
	def test_empty_query_matches_the_first_title(self):
		# Not 'exact': an empty query is how the palette opens, and every
		# command must stay in one bucket for the title sort to order them.
		self.assertEqual(
			(1, 0, []), self._match(['set window opacity'], [], '')
		)

	def _match(self, titles, keywords, query):
		return match_titles_or_keywords(
			self._MATCHERS, titles, keywords, query
		)
