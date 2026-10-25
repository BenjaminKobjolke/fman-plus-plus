from fman.impl.model.icon_set import list_icon_sets
# The bundled families and the guard that keeps them loadable live in
# test_fonts, next to each other; this module only holds the *themes* to
# them.
from fman_unittest.impl.test_fonts import bundled_font_families
from fman.impl.themes import DEFAULT_COLORS, DEFAULT_FONT, \
	DEFAULT_ICON_SIZE_PX, DEFAULT_THEME, DEFAULT_TOKENS, FALLBACKS, \
	MAX_ICON_SIZE, MIN_ICON_SIZE, MIN_OPACITY, build_main_window_palette, \
	build_palette, build_progress_bar_palette, build_tokens, \
	is_valid_color, list_themes, load_backgrounds, load_font, \
	load_icon_color, load_icon_set_name, load_icon_size, load_opacity, \
	load_theme, resolve_colors, scale_icon_size, substitute
from os.path import dirname, exists, join
from PyQt5.QtGui import QColor, QPalette
from tempfile import TemporaryDirectory
from unittest import TestCase

import json
import re

_PROJECT_DIR = dirname(dirname(dirname(dirname(dirname(dirname(
	__file__
))))))
_RESOURCES = join(_PROJECT_DIR, 'src', 'main', 'resources')
_THEMES_DIR = join(_RESOURCES, 'base', 'Themes')
_ICONS_DIR = join(_RESOURCES, 'base', 'Icons')
# The two files whose colors the themes own. Any other .qss stays literal on
# purpose - see docs/THEMES.md ("Not themed").
_TEMPLATES = (
	join(_RESOURCES, 'base', 'styles.qss'),
	join(_RESOURCES, 'base', 'Plugins', 'Core', 'Theme.css')
)

_COLOR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}\b|\b(?:white|black)\b')
_PLACEHOLDER = re.compile(r'\$([_a-zA-Z][_a-zA-Z0-9]*)')

def _read(path):
	with open(path, 'r', encoding='utf-8') as f:
		return f.read()

class SubstituteTest(TestCase):
	def test_replaces_known_tokens(self):
		self.assertEqual(
			'color: #123456;', substitute('color: $foo;', {'foo': '#123456'})
		)
	def test_leaves_unknown_token(self):
		# safe_substitute, so a user's own Theme.css can contain a '$'
		# without failing to load.
		self.assertEqual('a $b c', substitute('a $b c', {'foo': 'x'}))
	def test_leaves_stray_dollar(self):
		self.assertEqual('100$ ', substitute('100$ ', {'foo': 'x'}))

class ResolveColorsTest(TestCase):
	def test_hidden_file_colors_follow_pane_foreground_at_sixty_percent(self):
		result = resolve_colors({'colors': {'pane_fg': '#abcdef'}})
		self.assertEqual('#99abcdef', result['pane_hidden_fg'])
	def test_explicit_hidden_file_color_wins(self):
		result = resolve_colors({'colors': {
			'pane_fg': '#abcdef', 'pane_hidden_fg': '#123456'
		}})
		self.assertEqual('#123456', result['pane_hidden_fg'])
	def test_hidden_directory_color_follows_directory_fallback(self):
		result = resolve_colors({'colors': {'pane_fg_dir': '#123456'}})
		self.assertEqual('#99123456', result['pane_hidden_fg_dir'])
		self.assertEqual('#99ffffff', resolve_colors({})['pane_hidden_fg_dir'])
	def test_empty_theme_is_the_default(self):
		self.assertEqual(DEFAULT_COLORS, resolve_colors({}))
	def test_overrides_only_what_it_names(self):
		result = resolve_colors({'colors': {'pane_fg': '#abcdef'}})
		self.assertEqual('#abcdef', result['pane_fg'])
		self.assertEqual(DEFAULT_COLORS['pane_bg'], result['pane_bg'])
	def test_fallback_inherits_from_parent(self):
		# base_bg follows pane_bg, so a theme cannot leave the text viewer
		# on the previous theme's background.
		result = resolve_colors({'colors': {'pane_bg': '#101010'}})
		self.assertEqual('#101010', result['base_bg'])
	def test_fallback_chain(self):
		# border -> popup_input_border -> popup_input_border_top
		result = resolve_colors({'colors': {'border': '#111111'}})
		self.assertEqual('#111111', result['popup_input_border_top'])
	def test_explicit_value_beats_fallback(self):
		result = resolve_colors(
			{'colors': {'pane_bg': '#101010', 'base_bg': '#202020'}}
		)
		self.assertEqual('#202020', result['base_bg'])
	def test_ignores_unknown_token(self):
		self.assertEqual(DEFAULT_COLORS, resolve_colors({'colors': {'nope': 'red'}}))
	def test_ignores_invalid_value(self):
		result = resolve_colors({'colors': {'pane_bg': 'red; } * { color: red'}})
		self.assertEqual(DEFAULT_COLORS['pane_bg'], result['pane_bg'])
	def test_fallback_parents_are_known_tokens(self):
		for token, parent in FALLBACKS.items():
			self.assertIn(token, DEFAULT_COLORS)
			self.assertIn(parent, DEFAULT_COLORS)

class IsValidColorTest(TestCase):
	def test_accepts_hex_and_name(self):
		self.assertTrue(is_valid_color('#ff0000'))
		self.assertTrue(is_valid_color('white'))
	def test_rejects_injection(self):
		self.assertFalse(is_valid_color('red; } * { background: red'))
	def test_rejects_nonsense(self):
		self.assertFalse(is_valid_color('#gg0000'))
		self.assertFalse(is_valid_color(12))

class TemplatesTest(TestCase):

	"""
	The guard that keeps colors out of the stylesheets. A hex literal that
	creeps back in would silently ignore the active theme; a mistyped $token
	would survive substitution and make tinycss reject the file, which takes
	the whole Core plugin down with it.
	"""

	def test_no_color_literals_left(self):
		for path in _TEMPLATES:
			self.assertEqual([], _COLOR_LITERAL.findall(_read(path)), path)
	def test_every_placeholder_is_a_known_token(self):
		# DEFAULT_TOKENS, not DEFAULT_COLORS: $font_family is a token that
		# is not a color, and it has to clear this guard like any other.
		for path in _TEMPLATES:
			for name in _PLACEHOLDER.findall(_read(path)):
				self.assertIn(name, DEFAULT_TOKENS, '%s in %s' % (name, path))
	def test_every_token_is_used(self):
		used = set()
		for path in _TEMPLATES:
			used.update(_PLACEHOLDER.findall(_read(path)))
		used.update(_PALETTE_TOKENS)
		self.assertEqual(set(), set(DEFAULT_COLORS) - used)
	def test_substitution_leaves_no_placeholder(self):
		for path in _TEMPLATES:
			self.assertNotIn('$', substitute(_read(path), DEFAULT_TOKENS), path)
	def test_font_family_token_is_quoted(self):
		# A family with a space in it (every bundled one has) would fall
		# apart in the QSS declaration unless build_tokens quotes it.
		self.assertEqual(
			'"Share Tech Mono"',
			build_tokens(DEFAULT_COLORS, 'Share Tech Mono')['font_family']
		)
	def test_tokens_are_the_colors_plus_the_font(self):
		self.assertEqual(
			set(DEFAULT_COLORS) | {'font_family'}, set(DEFAULT_TOKENS)
		)
		for token, value in DEFAULT_COLORS.items():
			self.assertEqual(value, DEFAULT_TOKENS[token], token)

class BundledThemesTest(TestCase):
	def test_default_theme_file_is_empty(self):
		# Monokai == DEFAULT_COLORS. An empty file is the only way to say
		# that without repeating every color.
		path = join(_THEMES_DIR, DEFAULT_THEME + '.json')
		self.assertTrue(exists(path), path)
		with open(path, 'r', encoding='utf-8') as f:
			self.assertEqual({}, json.load(f))
	def test_themes_are_valid(self):
		names = list_themes([_THEMES_DIR])
		self.assertIn(DEFAULT_THEME, names)
		self.assertEqual(13, len(names), names)
		for name in names:
			with open(join(_THEMES_DIR, name + '.json'), 'r') as f:
				data = json.load(f)
			for token, value in (data.get('colors') or {}).items():
				self.assertIn(token, DEFAULT_COLORS, '%s: %s' % (name, token))
				self.assertTrue(
					is_valid_color(value), '%s: %s=%r' % (name, token, value)
				)
			# A value the validators reject is silently ignored at runtime,
			# which in a *bundled* theme is a typo nobody would notice.
			for key, load in (
				('opacity', load_opacity),
				('icon_size', load_icon_size),
				('icons', load_icon_set_name),
				('icon_color', load_icon_color),
				('font', load_font)
			):
				if key in data:
					self.assertEqual(
						data[key], load(name, [_THEMES_DIR]),
						'%s: %s=%r' % (name, key, data[key])
					)
			if 'backgrounds' in data:
				# Same reason, but it cannot join the loop above: the
				# loader answers Background tuples, not the raw JSON. An
				# entry fman drops is one whose image file went missing
				# from the resources tree, or whose fit/anchor is a typo.
				self.assertEqual(
					len(data['backgrounds']),
					len(load_backgrounds(name, [_THEMES_DIR])),
					'%s: backgrounds=%r' % (name, data['backgrounds'])
				)
			if 'icons' in data:
				# A bundled theme may only name a set fman actually ships.
				self.assertIn(
					data['icons'], list_icon_sets([_ICONS_DIR]),
					'%s: icons=%r' % (name, data['icons'])
				)
			if 'font' in data:
				# Likewise a family fman actually bundles. A theme *may* name
				# any family the machine has, but a bundled one that did would
				# look different on every machine.
				self.assertIn(
					data['font'], bundled_font_families(),
					'%s: font=%r' % (name, data['font'])
				)
	def test_windows_11_themes_keep_the_shell_icons(self):
		# Explorer uses the System icons; naming an icon set or font would make
		# these themes less like Explorer.
		for name in ('Windows 11 Light', 'Windows 11 Dark'):
			with open(join(_THEMES_DIR, name + '.json'), 'r', encoding='utf-8') as f:
				data = json.load(f)
			self.assertNotIn('icons', data, name)
			self.assertNotIn('font', data, name)
	def test_monokai_keeps_the_platform_font(self):
		# The pinned pre-fonts look: the default theme names no family, so
		# DEFAULT_FONT - the literal its platform's Theme.css used to
		# hardcode - is what applies.
		self.assertIsNone(load_font(DEFAULT_THEME, [_THEMES_DIR]))
		self.assertTrue(DEFAULT_FONT)
	def test_load_theme_falls_back_when_missing(self):
		self.assertEqual(DEFAULT_COLORS, load_theme('Nonexistent', [_THEMES_DIR]))
	def test_default_is_listed_without_any_dir(self):
		self.assertEqual([DEFAULT_THEME], list_themes([]))

class OpacityTest(TestCase):

	"""
	`opacity` is the one thing a theme may say that is not a color. It gets
	its own reader because resolve_colors drops everything that is not a
	valid color - a number could never survive inside "colors".
	"""

	def test_reads_the_key(self):
		self.assertEqual(0.8, self._load_opacity({'opacity': 0.8}))
	def test_reads_an_int(self):
		self.assertEqual(1.0, self._load_opacity({'opacity': 1}))
	def test_bundled_theme(self):
		self.assertEqual(0.92, load_opacity('Matrix', [_THEMES_DIR]))
	def test_theme_without_the_key(self):
		self.assertIsNone(load_opacity('Nord', [_THEMES_DIR]))
	def test_missing_theme(self):
		self.assertIsNone(load_opacity('Nonexistent', [_THEMES_DIR]))
	def test_rejects_a_string(self):
		self.assertIsNone(self._load_opacity({'opacity': '0.8'}))
	def test_rejects_a_bool(self):
		# True is an int in Python and would otherwise read as "opaque".
		self.assertIsNone(self._load_opacity({'opacity': True}))
	def test_rejects_too_transparent(self):
		self.assertIsNone(self._load_opacity({'opacity': MIN_OPACITY / 2}))
	def test_rejects_more_than_opaque(self):
		self.assertIsNone(self._load_opacity({'opacity': 1.5}))
	def test_non_dict_file_does_not_raise(self):
		# [] is valid JSON. Before this was guarded, .get('colors') on it
		# raised AttributeError out of load_theme - i.e. fman not starting.
		with TemporaryDirectory() as dir_:
			self._write(dir_, [])
			self.assertIsNone(load_opacity('T', [dir_]))
			self.assertEqual(DEFAULT_COLORS, load_theme('T', [dir_]))
	def _load_opacity(self, theme_json):
		with TemporaryDirectory() as dir_:
			self._write(dir_, theme_json)
			return load_opacity('T', [dir_])
	def _write(self, dir_, theme_json):
		with open(join(dir_, 'T.json'), 'w') as f:
			json.dump(theme_json, f)

class NonColorKeysTest(TestCase):

	"""
	The five things a theme may say that are not colors all go through one
	reader, so they are checked with one table: what the key is called, what
	it accepts, and what it refuses. `opacity`'s own edge cases stay in
	OpacityTest above - this is about the shared read-and-validate path.
	"""

	_CASES = (
		('opacity', load_opacity, 0.8, ('0.8', True, None, 1.5)),
		(
			'icon_size', load_icon_size, 20,
			('20', True, 20.5, MIN_ICON_SIZE - 1, MAX_ICON_SIZE + 1, None)
		),
		(
			'icons', load_icon_set_name, 'Material',
			('', 5, True, None, '..', '../elsewhere')
		),
		(
			'icon_color', load_icon_color, '#00ff41',
			('', 5, True, None, 'not-a-color', 'red; } * { color: red')
		),
		(
			'font', load_font, 'JetBrains Mono',
			# No 'not-a-font' here: unlike a color, a family fman has never
			# heard of is legal - Qt falls back on its own. Only the shapes
			# that could break out of the QSS declaration are refused.
			(
				'', '   ', 5, True, None, 'a; } * { color: red',
				'a { b', 'a } b', 'Say "Hi"'
			)
		)
	)

	def test_reads_the_key(self):
		for key, load, good, _ in self._CASES:
			with self.subTest(key):
				self.assertEqual(good, self._load(load, {key: good}))
	def test_rejects_unusable_values(self):
		for key, load, _, bad_values in self._CASES:
			for bad in bad_values:
				with self.subTest('%s=%r' % (key, bad)):
					self.assertIsNone(self._load(load, {key: bad}))
	def test_theme_without_the_key(self):
		for key, load, _, _bad in self._CASES:
			with self.subTest(key):
				self.assertIsNone(self._load(load, {'colors': {}}))
	def test_missing_theme(self):
		for key, load, _, _bad in self._CASES:
			with self.subTest(key):
				self.assertIsNone(load('Nonexistent', [_THEMES_DIR]))
	def test_non_dict_file_does_not_raise(self):
		for key, load, _, _bad in self._CASES:
			with self.subTest(key):
				self.assertIsNone(self._load(load, []))
	def test_icon_color_accepts_the_forms_qt_understands(self):
		for value in ('#0f4', '#00ff41', 'white'):
			with self.subTest(value):
				self.assertEqual(
					value, self._load(load_icon_color, {'icon_color': value})
				)
	def test_icon_size_accepts_the_whole_range(self):
		for value in (MIN_ICON_SIZE, MAX_ICON_SIZE):
			with self.subTest(value):
				self.assertEqual(
					value, self._load(load_icon_size, {'icon_size': value})
				)
	def test_font_accepts_a_family_nobody_has(self):
		# The point of the rule above, stated as its own case: an unknown
		# family is the theme author's problem to see, not fman's to reject.
		self.assertEqual(
			'Nonexistent Sans',
			self._load(load_font, {'font': 'Nonexistent Sans'})
		)
	def _load(self, load, theme_json):
		with TemporaryDirectory() as dir_:
			with open(join(dir_, 'T.json'), 'w') as f:
				json.dump(theme_json, f)
			return load('T', [dir_])

class ScaleIconSizeTest(TestCase):

	"""
	Growing the icons with the pane font zoom. The size that comes out is
	what the file list draws; the one that goes in is what the user or the
	theme asked for, which is why factor 1.0 has to be exactly transparent.
	"""

	def test_no_zoom_changes_nothing(self):
		for size in (None, MIN_ICON_SIZE, 16, MAX_ICON_SIZE):
			with self.subTest(size):
				self.assertEqual(size, scale_icon_size(size, 1.0))
	def test_unset_size_scales_from_qts_default(self):
		# None means "don't ask Qt for a size", which cannot be multiplied -
		# so the zoom has to know the number Qt would have used.
		self.assertEqual(
			DEFAULT_ICON_SIZE_PX * 2, scale_icon_size(None, 2.0)
		)
	def test_scales_from_the_chosen_size(self):
		# "Set icon size 24" then zoom in: the icons grow from 24, not from
		# Qt's 16.
		self.assertEqual(48, scale_icon_size(24, 2.0))
	def test_rounds_to_whole_pixels(self):
		self.assertEqual(18, scale_icon_size(16, 9 / 8))
	def test_clamps_to_the_supported_range(self):
		self.assertEqual(MAX_ICON_SIZE, scale_icon_size(48, 10.0))
		self.assertEqual(MIN_ICON_SIZE, scale_icon_size(16, 0.1))

# Every token the palette builders read. Kept next to the assertions below
# so the "every token is used" test above sees the palette-only ones too.
_PALETTE_TOKENS = frozenset((
	'window_bg', 'main_window_bg', 'base_bg', 'alt_row_bg', 'button_bg',
	'button_fg', 'palette_midlight', 'palette_mid', 'palette_dark',
	'palette_shadow', 'pane_cursor_bg', 'bright_fg'
))

class BuildPaletteTest(TestCase):

	"""
	Pins the palette to the values application_context.py hardcoded before
	themes existed, so the default theme is provably the old look.
	"""

	_EXPECTED = (
		(QPalette.Window, QColor(43, 43, 43)),
		(QPalette.WindowText, QColor('white')),
		(QPalette.Base, QColor(19, 19, 19)),
		(QPalette.AlternateBase, QColor(66, 64, 59)),
		(QPalette.ToolTipBase, QColor(19, 19, 19)),
		(QPalette.ToolTipText, QColor('white')),
		(QPalette.Light, QColor(0x49, 0x48, 0x3E)),
		(QPalette.Midlight, QColor(0x33, 0x33, 0x33)),
		(QPalette.Button, QColor(0x29, 0x29, 0x29)),
		(QPalette.Mid, QColor(0x25, 0x25, 0x25)),
		(QPalette.Dark, QColor(0x20, 0x20, 0x20)),
		(QPalette.Shadow, QColor(0x1d, 0x1d, 0x1d)),
		(QPalette.Text, QColor('white')),
		(QPalette.ButtonText, QColor(0xb6, 0xb3, 0xab)),
		(QPalette.Link, QColor('white')),
		(QPalette.LinkVisited, QColor('white'))
	)

	def test_matches_legacy_palette(self):
		palette = build_palette(DEFAULT_COLORS)
		for role, expected in self._EXPECTED:
			self.assertEqual(expected, palette.color(role), role)
	def test_inactive_highlight_avoids_blue(self):
		palette = build_palette(DEFAULT_COLORS)
		self.assertEqual(
			palette.color(QPalette.Midlight),
			palette.color(QPalette.Inactive, QPalette.Highlight)
		)
	def test_main_window_overrides_window_only(self):
		palette = build_main_window_palette(DEFAULT_COLORS)
		self.assertEqual(QColor(0x44, 0x44, 0x44), palette.color(QPalette.Window))
		self.assertEqual(QColor(19, 19, 19), palette.color(QPalette.Base))
	def test_progress_bar_keeps_highlight_when_inactive(self):
		palette = build_progress_bar_palette(DEFAULT_COLORS)
		self.assertEqual(
			palette.color(QPalette.Active, QPalette.Highlight),
			palette.color(QPalette.Inactive, QPalette.Highlight)
		)

def _relative_luminance(color):
	def channel(value):
		value /= 255
		return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
	c = QColor(color)
	return 0.2126 * channel(c.red()) \
		+ 0.7152 * channel(c.green()) \
		+ 0.0722 * channel(c.blue())

def contrast_ratio(foreground, background):
	"""WCAG 2.1 contrast ratio, 1:1 (identical) to 21:1 (black on white)."""
	a, b = _relative_luminance(foreground), _relative_luminance(background)
	return (max(a, b) + 0.05) / (min(a, b) + 0.05)

class LegibilityTest(TestCase):

	"""
	Every bundled theme has to be readable, not merely valid. The command
	palette is the case that bit us: `popup_divider_*` used to fall back to
	`popup_bg`, so in every theme but Monokai the entry separators were the
	same color as the surface they sat on and the list read as one block.

	Monokai is exempt: it *is* the look fman shipped before themes existed
	(BuildPaletteTest and TemplatesTest pin those exact values), so changing
	its colors to satisfy a ratio would break the guarantee that the default
	theme is unchanged.
	"""

	_LEGACY = frozenset(['Monokai'])
	# Themes that draw *no* entry separators on purpose: their divider
	# tokens are set to popup_bg deliberately, not by the old fallback bug
	# (test_no_separator_inherits_its_own_surface still guards that).
	_NO_DIVIDERS = frozenset(['Matrix'])
	# WCAG AA for body text. The palette's smallest text (the description
	# line) is what this protects.
	_MIN_TEXT = 4.5
	# Separators and the selected row are large areas, not text: they only
	# have to be *distinguishable* from the surface behind them.
	_MIN_SEPARATOR = 1.15
	_MIN_SELECTION = 1.35

	_TEXT_PAIRS = (
		('entry title', 'popup_item_fg', 'popup_bg'),
		('matched characters', 'bright_fg', 'popup_bg'),
		('shortcut hint', 'bright_fg', 'popup_bg'),
		('entry description', 'muted_fg', 'popup_bg'),
		('title on selected row', 'popup_item_fg', 'popup_selected_bg'),
		('query field', 'popup_input_fg', 'popup_input_bg'),
		('file row', 'pane_fg', 'pane_bg'),
		('directory row', 'pane_fg_dir', 'pane_bg'),
		('column header', 'muted_fg', 'header_bg')
	)

	def test_palette_text_is_readable(self):
		for name, colors in self._themes():
			for what, fg, bg in self._TEXT_PAIRS:
				ratio = contrast_ratio(colors[fg], colors[bg])
				self.assertGreaterEqual(
					ratio, self._MIN_TEXT,
					'%s: %s is %.1f:1 (%s on %s)'
					% (name, what, ratio, colors[fg], colors[bg])
				)
	def test_palette_separators_are_visible(self):
		for name, colors in self._themes():
			if name in self._NO_DIVIDERS:
				continue
			for token in ('popup_divider_top', 'popup_divider_bottom'):
				ratio = contrast_ratio(colors[token], colors['popup_bg'])
				self.assertGreaterEqual(
					ratio, self._MIN_SEPARATOR,
					'%s: %s is invisible against popup_bg (%.2f:1)'
					% (name, token, ratio)
				)
	def test_selected_row_stands_out(self):
		for name, colors in self._themes():
			ratio = contrast_ratio(colors['popup_selected_bg'], colors['popup_bg'])
			self.assertGreaterEqual(
				ratio, self._MIN_SELECTION,
				'%s: selected row barely differs from the popup (%.2f:1)'
				% (name, ratio)
			)
	def test_no_separator_inherits_its_own_surface(self):
		# The root cause, asserted directly: a separator whose fallback is
		# the surface it is drawn on can never be seen, whatever the theme.
		for token in (
			'popup_divider_top', 'popup_divider_bottom',
			'popup_query_inner_border', 'popup_input_border'
		):
			self.assertNotEqual('popup_bg', FALLBACKS.get(token), token)
	def _themes(self):
		for name in list_themes([_THEMES_DIR]):
			if name not in self._LEGACY:
				yield name, load_theme(name, [_THEMES_DIR])
