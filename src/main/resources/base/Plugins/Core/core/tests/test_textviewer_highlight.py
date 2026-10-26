from unittest import TestCase

from pygments.token import Name

from core.textviewer_highlight import (
	MAX_HIGHLIGHT_CHARS,
	get_spans,
	lexer_for_path,
	split_spans,
	style_name_for_background,
)


class SplitSpansTest(TestCase):
	def test_splits_multiline_token_into_line_local_spans(self):
		self.assertEqual(
			[[(0, 3, Name)], [(0, 3, Name)]],
			split_spans([(Name, 'one\ntwo')], 'one\ntwo')
		)

	def test_keeps_offsets_when_tokens_change_within_a_line(self):
		self.assertEqual(
			[[(0, 2, Name), (2, 3, Name)]],
			split_spans([(Name, 'ab'), (Name, 'cde')], 'abcde')
		)


class LexerLookupTest(TestCase):
	def test_resolves_known_filenames_and_rejects_unknown_or_missing_paths(self):
		self.assertIsNotNone(lexer_for_path('a.json'))
		self.assertIsNotNone(lexer_for_path('a.py'))
		self.assertIsNone(lexer_for_path('a.unknownext'))
		self.assertIsNone(lexer_for_path(None))

	def test_text_over_the_limit_gets_no_spans(self):
		self.assertEqual([], get_spans('x' * (MAX_HIGHLIGHT_CHARS + 1), 'a.py'))


class StyleSelectionTest(TestCase):
	def test_background_selects_dark_or_light_style(self):
		self.assertEqual('monokai', style_name_for_background('#202020'))
		self.assertEqual('default', style_name_for_background('#f0f0f0'))
