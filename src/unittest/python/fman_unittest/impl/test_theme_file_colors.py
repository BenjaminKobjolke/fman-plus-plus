from fman.impl.themes import (
	DEFAULT_COLORS, DEFAULT_THEME, FILE_COLOR_TOKENS, list_themes, load_theme
)
from os.path import dirname, join
from unittest import TestCase

import json

_PROJECT_DIR = dirname(dirname(dirname(dirname(dirname(dirname(__file__))))))
_THEMES_DIR = join(_PROJECT_DIR, 'src', 'main', 'resources', 'base', 'Themes')


class ThemeFileColorsTest(TestCase):
	def test_file_color_tokens_have_default_colors(self):
		for token in FILE_COLOR_TOKENS:
			with self.subTest(token=token):
				self.assertIn(token, DEFAULT_COLORS)

	def test_every_non_default_theme_sets_file_color_tokens(self):
		for name in list_themes([_THEMES_DIR]):
			if name == DEFAULT_THEME:
				continue
			with self.subTest(theme=name):
				with open(join(_THEMES_DIR, name + '.json'), encoding='utf-8') as f:
					colors = json.load(f).get('colors', {})
				self.assertTrue(
					all(token in colors for token in FILE_COLOR_TOKENS)
				)

	def test_file_colors_are_distinct_from_selection_color(self):
		for name in list_themes([_THEMES_DIR]):
			colors = load_theme(name, [_THEMES_DIR])
			with self.subTest(theme=name):
				for token in FILE_COLOR_TOKENS:
					self.assertNotEqual(
						colors[token], colors['pane_selected_fg'], token
					)
