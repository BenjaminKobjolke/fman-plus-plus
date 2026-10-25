from collections import OrderedDict
from fman.impl.themes import DEFAULT_TOKENS, substitute
from fman.impl.util.css import parse_css, CSSEngine
from tinycss.parsing import ParseError

class Theme:

	_CSS_TO_QSS = {
		'*': '*',
		'th': 'QTableView QHeaderView::section',
		'.statusbar': 'QStatusBar, QStatusBar QLabel, PaneStatusLine',
		'.quicksearch-query': 'Quicksearch QLineEdit',
		'.quicksearch-item': 'Quicksearch QListView::item',
		'.locationbar': 'LocationBar:read-only'
	}

	def __init__(self, app, qss_file_paths, tokens=None):
		self._app = app
		self._tokens = DEFAULT_TOKENS if tokens is None else tokens
		# Kept (rather than only their concatenated text) because switching
		# theme has to re-substitute the tokens in them:
		self._qss_file_paths = list(qss_file_paths)
		self._qss_base = self._build_qss_base()
		self._css_rules = OrderedDict()
		self._extra_qss_from_css = OrderedDict()
		# The raw, un-substituted bytes of every loaded CSS file, keyed by
		# path in load order - same reason as _qss_file_paths above.
		self._css_sources = OrderedDict()
		self._quicksearch_item_css = ''
		# The pane font zoom, so the command palette grows and shrinks with
		# the panes. Pushed by ThemeController, never saved here - see
		# set_font_scale.
		self._font_scale = 1.0
		self._updates_enabled = False
	def set_tokens(self, tokens):
		"""
		Applies a theme's tokens - its colors plus its font family, see
		fman.impl.themes.build_tokens - to the base style sheet and to every
		CSS file loaded so far, then restyles the app once. Load order is
		preserved, so a user's own Theme.css keeps winning over the theme.
		"""
		self._tokens = tokens
		self._qss_base = self._build_qss_base()
		updates_enabled = self._updates_enabled
		self._updates_enabled = False
		try:
			for css_file_path, f_contents in list(self._css_sources.items()):
				self._parse(css_file_path, f_contents)
		finally:
			self._updates_enabled = updates_enabled
		self._update_app()
	def load(self, css_file_path):
		with open(css_file_path, 'rb') as f:
			f_contents = f.read()
		self._parse(css_file_path, f_contents)
		self._css_sources[css_file_path] = f_contents
		self._update_app()
	def unload(self, css_file_path):
		del self._css_rules[css_file_path]
		del self._extra_qss_from_css[css_file_path]
		del self._css_sources[css_file_path]
		self._quicksearch_item_css = self._get_quicksearch_item_css()
		self._update_app()
	def get_quicksearch_item_css(self):
		return self._quicksearch_item_css
	def set_font_scale(self, factor):
		"""
		Scales every font size the command palette draws by `factor`, so it
		follows the pane font zoom. Deliberately not remembered here, for the
		same reason ThemeController.set_icon_scale isn't: the zoom that
		decides `factor` is the Core plugin's pane_font_size, which persists
		and is re-applied on startup already.
		"""
		self._font_scale = factor
		self._quicksearch_item_css = self._get_quicksearch_item_css()
		self._update_app()
	def enable_updates(self):
		"""
		Performance optimization: Updating our app's style sheet to reflect
		theme changes is a potentially expensive operation. So we don't want to
		do it after each plugin is loaded when fman starts. Instead, we disable
		updates in the beginning and only enable them once all plugins have been
		loaded.
		"""
		self._updates_enabled = True
		self._update_app()
	def _build_qss_base(self):
		result = ''
		for qss_file_path in self._qss_file_paths:
			with open(qss_file_path, 'r') as f:
				result += substitute(f.read(), self._tokens) + '\n'
		return result
	def _parse(self, css_file_path, f_contents):
		# Raises ThemeError. Kept separate from load(...) so switching theme
		# can re-parse an already-loaded file with the new colors, without
		# reading it from disk again.
		css = substitute(f_contents.decode('utf-8'), self._tokens)
		try:
			new_rules = parse_css(css.encode('utf-8'))
		except ParseError as e:
			raise ThemeError(
				'CSS Parse error in file %s at line %d, column %d: %s'
				% (css_file_path, e.line, e.column, e.reason)
			)
		self._css_rules[css_file_path] = new_rules
		self._extra_qss_from_css[css_file_path] = \
			'\n'.join(map(self._css_rule_to_qss, new_rules))
		try:
			self._quicksearch_item_css = self._get_quicksearch_item_css()
		except ValueError as e:
			error_message = 'CSS error in %s: %s' % (css_file_path, e)
			raise ThemeError(error_message) from None
	def _get_quicksearch_item_css(self):
		engine = self._css_engine()
		def scaled_pts(selector):
			return self._scale_pts(engine.parse_pts(selector, 'font-size'))
		return {
			'padding-top_px':
				engine.parse_px('.quicksearch-item', 'padding-top'),
			'padding-left_px':
				engine.parse_px('.quicksearch-item', 'padding-left'),
			'padding-right_px':
				engine.parse_px('.quicksearch-item', 'padding-right'),
			'border-top-width_px':
				engine.parse_border_width('.quicksearch-item', 'border-top'),
			'border-bottom-width_px':
				engine.parse_border_width('.quicksearch-item', 'border-bottom'),
			'title': {
				'font-size_pts': scaled_pts('.quicksearch-item-title'),
				'color': engine.parse_color('.quicksearch-item-title', 'color'),
				'highlight': {
					'color': engine.parse_color(
						'.quicksearch-item-title-highlight', 'color'
					)
				}
			},
			'hint': {
				'font-size_pts': scaled_pts('.quicksearch-item-hint'),
				'color': engine.parse_color('.quicksearch-item-hint', 'color')
			},
			'description': {
				'font-size_pts': scaled_pts('.quicksearch-item-description'),
				'color':
					engine.parse_color('.quicksearch-item-description', 'color')
			}
		}
	def _css_engine(self):
		return CSSEngine([r for rs in self._css_rules.values() for r in rs])
	def _scale_pts(self, pts):
		return max(1, round(pts * self._font_scale))
	def _get_font_scale_qss(self):
		# The palette's items are painted by hand from
		# get_quicksearch_item_css, but its query line is a real widget, so
		# its share of the zoom has to land as QSS - last, which is what
		# makes it win over the theme's own rule for the same selector.
		if self._font_scale == 1.0 or not self._css_rules:
			return ''
		try:
			pts = self._scale_pts(
				self._css_engine().parse_pts('.quicksearch-query', 'font-size')
			)
		except ValueError:
			# No theme loaded so far says how big the query line is; there is
			# then nothing to scale, and Qt's own default applies.
			return ''
		return '\nQuicksearch QLineEdit {\n\tfont-size: %dpt;\n}' % pts
	def _css_rule_to_qss(self, rule):
		qss_selectors = self._get_qss_selectors(rule.selectors)
		if not qss_selectors:
			return ''
		result = ', '.join(qss_selectors) + ' {'
		for decl in rule.declarations:
			result += '\n\t%s: %s;' % decl
		result += '\n}'
		return result
	def _get_qss_selectors(self, css_selectors):
		result = []
		for css_selector in css_selectors:
			try:
				result.append(self._CSS_TO_QSS[css_selector])
			except KeyError:
				continue
		return result
	def _update_app(self):
		if not self._updates_enabled:
			return
		qss = self._qss_base + ''.join(self._extra_qss_from_css.values()) + \
			  self._get_font_scale_qss()
		self._app.set_style_sheet(qss)

class ThemeError(Exception):
	@property
	def description(self):
		return self.args[0]
