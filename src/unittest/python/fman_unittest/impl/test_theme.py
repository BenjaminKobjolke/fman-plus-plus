from fman.impl.theme import Theme
from fman.impl.themes import DEFAULT_TOKENS, build_tokens
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase

_BASE_QSS = (
	'QTableView { background-color: $pane_bg; }\n'
	'* { font-family: $font_family; }\n'
)
# The declarations Theme._get_quicksearch_item_css() insists on. Every real
# Theme.css has them; a test one has to as well or load() raises.
_QUICKSEARCH_CSS = """
.quicksearch-item {
	padding-top: 1px;
	padding-left: 4px;
	padding-right: 4px;
	border-top: 1px solid $popup_divider_top;
	border-bottom: 1px solid $popup_divider_bottom;
}
.quicksearch-query { font-size: 10pt; }
.quicksearch-item-title { font-size: 10pt; color: $popup_item_fg; }
.quicksearch-item-title-highlight { color: $bright_fg; }
.quicksearch-item-hint { font-size: 8pt; color: $bright_fg; }
.quicksearch-item-description { font-size: 8pt; color: $muted_fg; }
"""
_CORE_LIKE_ZOOM_CSS = """
* { font-size: 9pt; }
th { font-size: 8pt; }
.statusbar { font-size: 8pt; }
.locationbar { font-size: 9pt; }
""" + _QUICKSEARCH_CSS.replace(
	'.quicksearch-query { font-size: 10pt; }',
	'.quicksearch-query { font-size: 12pt; }'
)

class StubApp:
	def __init__(self):
		self.stylesheet = None
	def set_style_sheet(self, stylesheet):
		self.stylesheet = stylesheet

class ThemeTest(TestCase):
	def test_base_qss_is_substituted(self):
		theme = self._make_theme()
		theme.enable_updates()
		self.assertIn(DEFAULT_TOKENS['pane_bg'], self._app.stylesheet)
		self.assertNotIn('$pane_bg', self._app.stylesheet)
	def test_font_family_is_substituted_quoted(self):
		theme = self._make_theme()
		theme.enable_updates()
		self.assertIn(
			'font-family: ' + DEFAULT_TOKENS['font_family'],
			self._app.stylesheet
		)
	def test_set_tokens_restyles_the_font(self):
		# A theme switch moves the family the same way it moves a color:
		# through the one stylesheet both tokens travel in.
		theme = self._make_theme()
		theme.enable_updates()
		theme.set_tokens(self._tokens(font='Share Tech Mono'))
		self.assertIn('font-family: "Share Tech Mono"', self._app.stylesheet)
	def test_set_tokens_restyles_base_qss(self):
		theme = self._make_theme()
		theme.enable_updates()
		theme.set_tokens(self._tokens(pane_bg='#123456'))
		self.assertIn('#123456', self._app.stylesheet)
	def test_set_tokens_reparses_loaded_css(self):
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _QUICKSEARCH_CSS))
		theme.enable_updates()
		theme.set_tokens(self._tokens(popup_item_fg='#abcdef'))
		title_color = theme.get_quicksearch_item_css()['title']['color']
		self.assertEqual('#abcdef', title_color.name())
	def test_css_layers_keep_their_order(self):
		# The user's own Theme.css loads last and must keep winning over the
		# theme's colors, also after a switch.
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _QUICKSEARCH_CSS))
		theme.load(self._write('User.css', '* { font-size: 14pt; }'))
		theme.enable_updates()
		theme.set_tokens(self._tokens(pane_bg='#123456'))
		stylesheet = self._app.stylesheet
		self.assertLess(
			stylesheet.index('#123456'), stylesheet.index('font-size: 14pt')
		)
	def test_statusbar_font_rule_covers_pane_status_lines(self):
		theme = self._make_theme()
		theme.load(self._write(
			'Theme.css', _QUICKSEARCH_CSS + '\n.statusbar { font-size: 8pt; }'))
		theme.enable_updates()
		self.assertIn(
			'QStatusBar, QStatusBar QLabel, PaneStatusLine {',
			self._app.stylesheet)
	def test_unload_forgets_the_source(self):
		theme = self._make_theme()
		path = self._write('Theme.css', _QUICKSEARCH_CSS)
		theme.load(path)
		theme.load(self._write('Other.css', _QUICKSEARCH_CSS))
		theme.unload(path)
		theme.enable_updates()
		# Would raise KeyError if unload had left the raw source behind:
		theme.set_tokens(self._tokens(popup_item_fg='#abcdef'))
	def test_font_offset_grows_the_palette_items_by_points(self):
		# The items are painted by hand, so their sizes travel in the css
		# dict rather than in the stylesheet.
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _QUICKSEARCH_CSS))
		theme.enable_updates()
		theme.set_font_offset(3)
		css = theme.get_quicksearch_item_css()
		self.assertEqual(13, css['title']['font-size_pts'])
		self.assertEqual(11, css['hint']['font-size_pts'])
	def test_font_offset_overrides_the_query_line_qss(self):
		# The query line is a real widget, so its size has to reach QSS -
		# and after the theme's own rule for the same selector.
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _QUICKSEARCH_CSS))
		theme.enable_updates()
		theme.set_font_offset(3)
		stylesheet = self._app.stylesheet
		self.assertIn(
			'Quicksearch QLineEdit {\n\tfont-size: 13pt;', stylesheet
		)
		self.assertLess(
			stylesheet.index('font-size: 10pt'),
			stylesheet.index('font-size: 13pt')
		)
	def test_font_offset_zooms_window_chrome_and_palette_header(self):
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _CORE_LIKE_ZOOM_CSS))
		theme.enable_updates()
		theme.set_font_offset(3)
		stylesheet = self._app.stylesheet
		for selector, size in (
			('Quicksearch #header, Quicksearch #footer, Quicksearch QListView', 12),
			('LocationBar:read-only', 12),
			('QTableView QHeaderView::section', 11),
			('QStatusBar, QStatusBar QLabel, PaneStatusLine', 11),
			('Quicksearch QLineEdit', 15),
		):
			self.assertIn(
				'%s {\n\tfont-size: %dpt;' % (selector, size), stylesheet
			)
	def test_zero_font_offset_does_not_add_zoom_rules(self):
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _CORE_LIKE_ZOOM_CSS))
		theme.enable_updates()
		theme.set_font_offset(0)
		self.assertEqual('', theme._get_font_zoom_qss())
	def test_font_offset_skips_only_selectors_without_a_base_size(self):
		css = _CORE_LIKE_ZOOM_CSS.replace('th { font-size: 8pt; }', '')
		theme = self._make_theme()
		theme.load(self._write('Theme.css', css))
		theme.enable_updates()
		theme.set_font_offset(3)
		stylesheet = self._app.stylesheet
		self.assertNotIn('QTableView QHeaderView::section {', stylesheet)
		for selector, size in (
			('Quicksearch #header, Quicksearch #footer, Quicksearch QListView', 12),
			('LocationBar:read-only', 12),
			('QStatusBar, QStatusBar QLabel, PaneStatusLine', 11),
			('Quicksearch QLineEdit', 15),
		):
			self.assertIn(
				'%s {\n\tfont-size: %dpt;' % (selector, size), stylesheet
			)
	def test_resetting_the_font_offset_drops_the_override(self):
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _QUICKSEARCH_CSS))
		theme.enable_updates()
		theme.set_font_offset(3)
		theme.set_font_offset(0)
		self.assertNotIn('font-size: 13pt', self._app.stylesheet)
		self.assertEqual(
			10, theme.get_quicksearch_item_css()['title']['font-size_pts']
		)
	def test_font_offset_clamps_palette_items_to_one_point(self):
		theme = self._make_theme()
		theme.load(self._write('Theme.css', _QUICKSEARCH_CSS))
		theme.enable_updates()
		theme.set_font_offset(-20)
		css = theme.get_quicksearch_item_css()
		self.assertEqual(1, css['title']['font-size_pts'])
		self.assertEqual(1, css['hint']['font-size_pts'])
	def setUp(self):
		super().setUp()
		self._app = StubApp()
		self._tmp_dir = TemporaryDirectory()
		self.addCleanup(self._tmp_dir.cleanup)
	def _tokens(self, font=None, **colors):
		# DEFAULT_TOKENS already carries the default family, so a test that
		# only moves a color does not have to know a font exists.
		result = dict(DEFAULT_TOKENS, **colors)
		if font is not None:
			result = build_tokens(result, font)
		return result
	def _make_theme(self):
		return Theme(self._app, [self._write('styles.qss', _BASE_QSS)])
	def _write(self, name, contents):
		result = join(self._tmp_dir.name, name)
		with open(result, 'w', encoding='utf-8') as f:
			f.write(contents)
		return result
