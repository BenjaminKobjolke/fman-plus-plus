from unittest import TestCase
from unittest.mock import patch

from core.file_colors import (
	DEFAULT_FILE_COLOR_RULES, apply, load_options, make_colorer
)
from fman.impl.themes import FILE_COLOR_TOKENS


class FileColorsTest(TestCase):
	def test_default_rules_use_theme_file_color_tokens_in_order(self):
		self.assertEqual(
			FILE_COLOR_TOKENS,
			tuple(rule['color'] for rule in DEFAULT_FILE_COLOR_RULES)
		)

	@patch('core.file_colors.get_setting', return_value=None)
	def test_missing_settings_use_defaults(self, get_setting):
		options = load_options()
		self.assertFalse(options.enabled)
		self.assertTrue(options.rules)

	@patch('core.file_colors.get_setting')
	def test_invalid_settings_use_safe_defaults(self, get_setting):
		get_setting.side_effect = [1, {'bad': 'rules'}]
		options = load_options()
		self.assertFalse(options.enabled)
		self.assertTrue(options.rules)

	@patch('core.file_colors.get_setting', side_effect=[False, [
		{'patterns': ['*.png'], 'color': '#fff'},
		{'patterns': [], 'color': '#000'},
	]])
	def test_invalid_rule_entries_are_skipped(self, get_setting):
		self.assertEqual(
			[{'patterns': ['*.png'], 'color': '#fff'}], load_options().rules
		)

	def test_invalid_rules_are_skipped(self):
		colorer = make_colorer([
			None, {}, {'patterns': [], 'color': '#fff'},
			{'patterns': ['*.png', 1], 'color': '#fff'},
			{'patterns': ['*.jpg'], 'color': 1},
			{'patterns': ['*.png'], 'color': '#fff'},
		])
		self.assertEqual('#fff', colorer('file:///images/PHOTO.PNG'))

	def test_first_matching_rule_wins_case_insensitively(self):
		colorer = make_colorer([
			{'patterns': ['*.png'], 'color': 'first'},
			{'patterns': ['*.PNG'], 'color': 'second'},
		])
		self.assertEqual('first', colorer('file:///images/PHOTO.PNG'))

	def test_no_match_returns_none(self):
		self.assertIsNone(make_colorer([])('file:///readme.txt'))

	@patch('core.file_colors.get_setting', side_effect=[False, []])
	def test_apply_clears_colorer_when_disabled(self, get_setting):
		pane = _Pane()
		apply(pane)
		self.assertIsNone(pane.colorer)

	@patch('core.file_colors.get_setting', side_effect=[True, []])
	def test_apply_sets_colorer_when_enabled(self, get_setting):
		pane = _Pane()
		apply(pane)
		self.assertTrue(callable(pane.colorer))
		self.assertIsNone(pane.colorer('file:///readme.txt'))


class _Pane:
	def set_file_coloring(self, colorer):
		self.colorer = colorer
