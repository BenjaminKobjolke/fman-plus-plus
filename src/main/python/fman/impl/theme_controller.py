"""
Applying a theme while fman is running.

fman.impl.themes owns the *data*: the color tokens, the six non-color keys
a theme file may carry, and the validators each of them answers to. This
module owns the *push* - resolving the user's choice against the theme's and
handing the result to the QApplication, the main window, the icon provider
and the Theme stylesheet engine. Split from themes.py so neither file has to
be read to understand the other. See docs/THEMES.md.
"""
from collections import namedtuple
from fman.impl.model.icon_set import DEFAULT_ICON_SET, ICON_SET_SETTING, \
	list_icon_sets, load_icon_set
from fman.impl.themes import DEFAULT_FONT, DEFAULT_ICON_COLOR, \
	DEFAULT_ICON_SIZE, DEFAULT_OPACITY, DEFAULT_THEME, FONT_SETTING, \
	ICON_COLOR_SETTING, ICON_SIZE_SETTING, MAX_ICON_SIZE, MIN_ICON_SIZE, \
	MIN_OPACITY, OPACITY_SETTING, THEME_SETTING, _normalize_font, \
	_normalize_icon_color, _normalize_icon_set_name, _normalize_icon_size, \
	_normalize_opacity, build_main_window_palette, build_palette, \
	build_progress_bar_palette, build_tokens, list_themes, load_backgrounds, \
	load_font, load_icon_color, load_icon_set_name, load_icon_size, \
	load_opacity, load_theme, scale_icon_size
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtGui import QFontDatabase

class _ThemeProperty(
	namedtuple('_ThemeProperty', 'setting normalize load default')
):
	"""
	One of the five things a theme carries that is not a color: its key in
	%APPDATA%/fman/Local/Settings.json, the validator that both the theme
	file and the user's own setting answer to, the reader for the theme
	file, and what applies when neither asks for anything. Bundled so
	ThemeController resolves all five through one chain instead of five
	copies of it - adding a sixth is a tuple, not another method.
	"""

_OPACITY = _ThemeProperty(
	OPACITY_SETTING, _normalize_opacity, load_opacity, DEFAULT_OPACITY
)
_ICON_SET = _ThemeProperty(
	ICON_SET_SETTING, _normalize_icon_set_name, load_icon_set_name,
	DEFAULT_ICON_SET
)
_ICON_SIZE = _ThemeProperty(
	ICON_SIZE_SETTING, _normalize_icon_size, load_icon_size, DEFAULT_ICON_SIZE
)
_ICON_COLOR = _ThemeProperty(
	ICON_COLOR_SETTING, _normalize_icon_color, load_icon_color,
	DEFAULT_ICON_COLOR
)
_FONT = _ThemeProperty(
	FONT_SETTING, _normalize_font, load_font, DEFAULT_FONT
)

# Everything a theme switch has to hand to the UI at once. set_theme
# resolves all of it for the *incoming* theme, because that theme's name is
# not saved yet when _apply runs.
#
# `backgrounds` is here but is deliberately *not* a sixth _ThemeProperty:
# that tuple exists to let a saved setting beat the theme's value, and
# the background images have no such setting - a theme file is the only
# place they can be written. A `setting` key nothing ever writes would be
# dead config.
_Appearance = namedtuple(
	'_Appearance',
	'colors opacity icon_set icon_size icon_color font backgrounds'
)

class ThemeController:

	"""
	Reads and switches the active theme. Takes the ApplicationContext rather
	than its five collaborators separately: everything a theme switch has to
	touch (the QApplication, the Theme, the main window, the settings file
	and the theme directories) already hangs off it, and the alternative is
	a five-argument constructor that has to be kept in sync with it anyway.
	"""

	def __init__(self, app_context):
		self._ctxt = app_context
		# Set by the Core plugin's pane font size commands, never saved here
		# - see set_icon_scale.
		self._icon_scale = 1.0

	def get_themes(self):
		return list_themes(self._ctxt.theme_dirs)

	def get_theme(self):
		return self._ctxt.local_settings.get(THEME_SETTING, DEFAULT_THEME)

	def set_theme(self, name):
		self._apply(self._get_appearance(name))
		settings = self._ctxt.local_settings
		settings[THEME_SETTING] = name
		settings.flush()

	def get_opacity(self):
		return self._get_opacity(self.get_theme())

	def get_backgrounds(self):
		"""
		The images the active theme places behind fman's UI, or an empty
		tuple if it places none. What ApplicationContext hands the window
		at startup, so there is no second place that knows how a theme's
		backgrounds are resolved.
		"""
		return self._load_backgrounds(self.get_theme())

	def get_icon_sets(self):
		return list_icon_sets(self._ctxt.icon_dirs)

	def get_icon_set(self):
		return self._get(_ICON_SET, self.get_theme())

	def set_icon_set(self, name):
		"""
		Applies icon set `name` and remembers it across restarts. name=None
		drops the override so the active theme decides again - the same
		"None clears the key" rule the plugin settings use. Panes still hold
		icons made under the old set; the Core plugin reloads them.
		"""
		if name is not None and _normalize_icon_set_name(name) is None:
			raise ValueError('Not a usable icon set name: %r' % (name,))
		self._save(_ICON_SET, name)
		self._ctxt.icon_provider.set_icon_set(
			self._load_icon_set(self.get_icon_set())
		)

	def get_icon_size(self):
		return self._get(_ICON_SIZE, self.get_theme())

	def set_icon_size(self, value):
		"""
		Applies icon size `value` (MIN_ICON_SIZE - MAX_ICON_SIZE) and
		remembers it. Pass None to follow the active theme again, which for
		a theme that asks for no size means Qt's own default. Raises
		ValueError for a size fman cannot use.
		"""
		if value is not None and _normalize_icon_size(value) is None:
			raise ValueError(
				'Icon size must be a whole number between %s and %s, not %r'
				% (MIN_ICON_SIZE, MAX_ICON_SIZE, value)
			)
		self._save(_ICON_SIZE, value)
		self._apply_icon_size(self.get_icon_size())

	def set_icon_scale(self, factor):
		"""
		Scales the drawn icon size by `factor`, so the icons follow the pane
		font zoom. Applied but deliberately *not* remembered: the zoom that
		decides `factor` is the Core plugin's pane_font_size, which is saved
		in Core Settings.json and re-applied on startup already. Saving it
		here too would give one zoom two homes that could disagree.

		This is why get_icon_size() keeps answering the unscaled size: that
		is the value the user picked, and the one "Set icon size" preselects.
		"""
		self._icon_scale = factor
		self._apply_icon_size(self.get_icon_size())

	def set_palette_font_scale(self, factor):
		"""
		Scales the command palette's font sizes by `factor`, so the palette
		follows the pane font zoom the way the icons do. Not remembered here
		either, and for the same reason - see set_icon_scale.

		Separate from set_icon_scale rather than folded into it: both take
		the same factor, but one is an image size and the other a stylesheet
		value, and a plugin may well want one without the other.
		"""
		self._ctxt.theme.set_font_scale(factor)

	def get_icon_color(self):
		return self._get(_ICON_COLOR, self.get_theme())

	def set_icon_color(self, value):
		"""
		Recolors the icon set's icons to `value` and remembers it across
		restarts. value=None drops the override so the active theme decides
		again. Raises ValueError for a color fman cannot use. Panes still
		hold icons tinted the old color; the Core plugin reloads them.
		"""
		if value is not None and _normalize_icon_color(value) is None:
			raise ValueError('Not a usable icon color: %r' % (value,))
		self._save(_ICON_COLOR, value)
		self._ctxt.icon_provider.set_icon_color(self.get_icon_color())

	def get_fonts(self):
		"""
		Every font family Qt can draw, sorted: the ones fman bundles (loaded
		from the Core plugin's Fonts directory, see impl/plugins/plugin.py)
		and the ones the operating system supplies, in one list. There is
		deliberately no separate registry of 'fonts fman offers' - it could
		only disagree with what Qt actually has.
		"""
		return self._list_font_families()

	def get_font(self):
		return self._get(_FONT, self.get_theme())

	def set_font(self, value):
		"""
		Draws the UI in font family `value` and remembers it across restarts.
		value=None drops the override so the active theme decides again.
		Raises ValueError for a family fman cannot use. A family Qt does not
		have is *not* an error: Qt falls back to its own font, the same as a
		theme naming a font the machine has never installed.
		"""
		if value is not None and _normalize_font(value) is None:
			raise ValueError('Not a usable font family: %r' % (value,))
		self._save(_FONT, value)
		# Through the whole appearance rather than a provider of its own: the
		# font is a stylesheet token, so the only thing that can push it is
		# the same Theme.set_tokens call a theme switch makes.
		self._apply(self._get_appearance(self.get_theme()))

	def set_opacity(self, value):
		"""
		Applies `value` and remembers it across restarts. value=None drops
		the override, so the active theme's opacity applies again - the same
		"None clears the key" rule the plugin settings use. Raises ValueError
		for a number fman cannot use.
		"""
		if value is not None and _normalize_opacity(value) is None:
			raise ValueError(
				'Opacity must be a number between %s and %s, not %r'
				% (MIN_OPACITY, DEFAULT_OPACITY, value)
			)
		self._save(_OPACITY, None if value is None else float(value))
		self._apply_opacity(self.get_opacity())

	def _get_opacity(self, theme_name):
		return self._get(_OPACITY, theme_name)

	def _get(self, prop, theme_name):
		# One precedence chain for all four non-color properties,
		# parameterized by theme name so set_theme can ask it about a theme
		# that is not the saved one yet: the user's own setting wins, then
		# what the theme asks for, then fman's default.
		# Never reads the value back off the widget: the window does not
		# exist yet when this first runs, and for opacity Qt quantizes to
		# 1/255, so a value read back never equals the one that was set.
		saved = prop.normalize(
			self._ctxt.local_settings.get(prop.setting, None)
		)
		if saved is not None:
			return saved
		from_theme = prop.load(theme_name, self._ctxt.theme_dirs)
		return prop.default if from_theme is None else from_theme

	def _save(self, prop, value):
		settings = self._ctxt.local_settings
		if value is None:
			settings.pop(prop.setting)
		else:
			settings[prop.setting] = value
		settings.flush()

	def _get_appearance(self, theme_name):
		return _Appearance(
			load_theme(theme_name, self._ctxt.theme_dirs),
			self._get(_OPACITY, theme_name),
			self._load_icon_set(self._get(_ICON_SET, theme_name)),
			self._get(_ICON_SIZE, theme_name),
			self._get(_ICON_COLOR, theme_name),
			self._get(_FONT, theme_name),
			self._load_backgrounds(theme_name)
		)

	@run_in_main_thread
	def _list_font_families(self):
		# QFontDatabase is a GUI class and commands run off the main thread
		# (see PaneCommandRegistry), so this has to hop like the appliers do.
		return sorted(QFontDatabase().families())

	def _load_icon_set(self, name):
		return load_icon_set(name, self._ctxt.icon_dirs)

	def _load_backgrounds(self, theme_name):
		return load_backgrounds(theme_name, self._ctxt.theme_dirs)

	@run_in_main_thread
	def _apply_opacity(self, opacity):
		self._ctxt.main_window.setWindowOpacity(opacity)

	@run_in_main_thread
	def _apply_icon_size(self, icon_size):
		# The one place the font zoom is folded in, so no caller has to
		# remember to do it.
		self._ctxt.main_window.set_file_list_icon_size(
			scale_icon_size(icon_size, self._icon_scale)
		)

	@run_in_main_thread
	def _apply(self, appearance):
		# Commands run off the main thread (see PaneCommandRegistry), and
		# touching QPalettes from there is not allowed.
		#
		# Palette first, style sheet second: QApplication.setStyleSheet
		# re-polishes every widget, which is what makes the new palette
		# actually repaint. The other order leaves stale colors behind.
		colors = appearance.colors
		self._ctxt.app.setPalette(build_palette(colors))
		main_window = self._ctxt.main_window
		main_window.setPalette(build_main_window_palette(colors))
		# Re-read for each new ProgressDialog (progress_dialog.py), so the next one
		# picks the new colors up without restarting fman:
		main_window.set_progress_bar_palette(
			build_progress_bar_palette(colors)
		)
		# A theme may ask for an opacity, an icon set, an icon size, an icon
		# color, a font and background images too, so switching theme has to
		# move all six - back to fman's defaults included, when the new theme
		# asks for nothing.
		main_window.setWindowOpacity(appearance.opacity)
		# Before the stylesheet below: set_backgrounds flips the property
		# the new QSS rules are keyed on, and setStyleSheet re-polishes
		# every widget, so this order restyles them once instead of twice.
		main_window.set_backgrounds(appearance.backgrounds)
		# The icons are image files, not stylesheet tokens, so they do not go
		# through Theme - not even the color, which is painted onto them
		# rather than substituted into QSS. Panes still hold icons made under
		# the old set and color; the Core plugin's SelectTheme reloads them.
		self._ctxt.icon_provider.set_icon_color(appearance.icon_color)
		self._ctxt.icon_provider.set_icon_set(appearance.icon_set)
		# Through _apply_icon_size, not set_file_list_icon_size directly: the
		# font zoom has to survive a theme switch.
		self._apply_icon_size(appearance.icon_size)
		# The font rides the stylesheet the colors already travel in, so it
		# needs no apply path of its own - build_tokens is the one place that
		# knows a family becomes the $font_family token.
		self._ctxt.theme.set_tokens(build_tokens(colors, appearance.font))
