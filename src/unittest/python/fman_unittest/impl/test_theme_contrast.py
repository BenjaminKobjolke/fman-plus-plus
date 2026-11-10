"""Protect readable text colors across bundled themes and themed dialogs."""

from fman.impl.themes import build_palette, list_themes, load_theme
from fman_unittest.impl.test_themes import _THEMES_DIR, contrast_ratio
from os.path import join
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication
from unittest import TestCase

import re


MIN_CONTRAST = 3.0
_TEXT_PAIRS = (
	('muted_fg', 'popup_bg'),
	('popup_item_fg', 'popup_bg'),
	('popup_item_fg', 'popup_selected_bg'),
	('popup_input_fg', 'popup_input_bg'),
	('muted_fg', 'pane_bg'),
	('bright_fg', 'pane_bg'),
	('bright_fg', 'popup_bg'),
	('bright_fg', 'input_bg')
)


class ThemeContrastTest(TestCase):
	def test_dialog_outline_differs_from_dialog_background_in_every_theme(self):
		for theme_name in list_themes([_THEMES_DIR]):
			colors = load_theme(theme_name, [_THEMES_DIR])
			with self.subTest(theme=theme_name):
				self.assertNotEqual(
					QColor(colors['border']).rgba(),
					QColor(colors['popup_bg']).rgba()
				)

	def test_text_background_pairs_have_minimum_contrast_in_every_theme(self):
		for theme_name in list_themes([_THEMES_DIR]):
			colors = load_theme(theme_name, [_THEMES_DIR])
			for fg_token, bg_token in _TEXT_PAIRS:
				with self.subTest(theme=theme_name, pair=(fg_token, bg_token)):
					ratio = contrast_ratio(colors[fg_token], colors[bg_token])
					self.assertGreaterEqual(
						ratio, MIN_CONTRAST,
						'%s on %s is %.1f:1' % (fg_token, bg_token, ratio)
					)

	def test_quicksearch_header_uses_a_text_token_contrasted_with_popup_bg(self):
		styles_path = join(
			_THEMES_DIR, '..', 'styles.qss'
		)
		with open(styles_path, 'r', encoding='utf-8') as f:
			styles = f.read()
		match = re.search(r'Quicksearch\s+#header\s*\{([^}]*)\}', styles)
		self.assertIsNotNone(match, 'Quicksearch #header rule not found')
		color = re.search(r'\bcolor\s*:\s*\$([\w]+)', match.group(1))
		self.assertIsNotNone(color, 'Quicksearch #header color token not found')
		allowed_tokens = {
			fg_token for fg_token, bg_token in _TEXT_PAIRS
			if bg_token == 'popup_bg'
		}
		self.assertIn(color.group(1), allowed_tokens)

	def test_highlight_uses_the_active_application_palette(self):
		from fman.impl.html_style import highlight

		palette = build_palette(load_theme('Light', [_THEMES_DIR]))
		self.app.setPalette(palette)
		color_name = palette.color(QPalette.WindowText).name()
		html = highlight('X')
		self.assertIn(color_name, html)
		self.assertNotIn('white', html)

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.old_palette = self.app.palette()

	def tearDown(self):
		self.app.setPalette(self.old_palette)
