"""
Color themes: the single source of truth for every color in fman's UI.

fman's look used to be spread over three places that could drift apart -
the hardcoded hex literals in resources/base/styles.qss, the QPalette built
in application_context.py, and the quicksearch item colors in
Plugins/Core/Theme.css. This module replaces all three with one flat map of
named color tokens:

  * styles.qss and Theme.css now contain `$token` placeholders which
    Theme (impl/theme.py) substitutes at load time and again on every theme
    switch.
  * build_palette(...) & co. derive the QPalette from the *same* tokens, so
    a theme cannot style the file list one way and the text viewer - which
    samples QPalette.Base - another.

A theme is one JSON file listing only the tokens it changes; everything else
falls back to DEFAULT_COLORS, which holds exactly the values fman shipped
before themes existed. That is what makes the default theme provably
identical to the old look: its file is empty.

Beside its colors a theme may carry six things that are not colors:
opacity, icon set, icon size, icon color, font family and background
images. The first five share one read-and-validate path
(_load_theme_value) and one precedence chain (ThemeController._get), so a
seventh of that shape is a key and a validator. The images are the
exception on both counts - see load_backgrounds and impl/background.py.

See docs/THEMES.md for the token reference and how to add a theme.
"""
from fman.impl.background import normalize_backgrounds
from fbs_runtime import platform
from fman.impl.model.icon_set import is_valid_icon_set_name
from glob import glob
from os.path import basename, join, splitext
from PyQt5.QtGui import QColor, QPalette
from string import Template

import json

# The theme used when the user has not picked one. Its JSON file is empty:
# DEFAULT_COLORS *is* Monokai.
DEFAULT_THEME = 'Monokai'

# The setting key in %APPDATA%/fman/Local/Settings.json. It lives there and
# not in Core Settings.json because the palette is built before any plugin
# (and thus fman.load_json) is available - see ApplicationContext.app.
THEME_SETTING = 'theme'

# The user's own window opacity, in the same file and for the same reason.
# It overrides whatever the active theme asks for; absent means "follow the
# theme". Below MIN_OPACITY the window is too faint to work in.
OPACITY_SETTING = 'window_opacity'
DEFAULT_OPACITY = 1.0
MIN_OPACITY = 0.3

# How big the file list draws its icons, in pixels. Also the user's own
# setting first, then the theme's. DEFAULT_ICON_SIZE is None rather than a
# number on purpose: it means "don't touch it", so Qt's own decorationSize
# (16px) stands and fman looks exactly as it did before this was themeable.
ICON_SIZE_SETTING = 'icon_size'
DEFAULT_ICON_SIZE = None
MIN_ICON_SIZE = 12
MAX_ICON_SIZE = 64
# The number DEFAULT_ICON_SIZE stands for. Only scale_icon_size needs it:
# "don't touch it" cannot be multiplied, so the zoom has to know what Qt
# would have drawn. Everywhere else None keeps meaning "don't ask Qt".
DEFAULT_ICON_SIZE_PX = 16

# What an icon set's icons are recolored to, or None to leave them alone.
# Same user-then-theme resolution as the three above. Only an icon set can
# answer to this: the OS icons DEFAULT_ICON_SET stands for are the shell's
# bitmaps, not files fman owns.
ICON_COLOR_SETTING = 'icon_color'
DEFAULT_ICON_COLOR = None

# The font family the whole UI is drawn in. Same user-then-theme
# resolution as the four above. Unlike them it has no "don't touch it"
# value: fman always sets a family, so the default is what each platform's
# Theme (<Platform>).css used to hardcode.
#
# Windows is 'Roboto', not the 'Roboto Bold' that CSS said. The bundled
# file is Roboto's Bold face, but a face is not a family: its name table
# says 'Roboto', so that is what QFontDatabase registers and 'Roboto Bold'
# matched nothing - Qt had been silently falling back for years. The family
# has only that one face, so asking for it still draws the bold weight fman
# always wanted, this time actually in Roboto.
FONT_SETTING = 'font'
_DEFAULT_FONTS = {
	'Windows': 'Roboto',
	# Open Sans.ttf is likewise a Semibold face registered under this name.
	'Linux': 'Open Sans',
	# Mac set no font-family at all, so this one is new. It is the family
	# fman already picks for its Mac context menus (resources/mac/
	# os_styles.qss), not a sixth opinion about how Mac should look.
	'Mac': 'Helvetica Neue'
}
DEFAULT_FONT = _DEFAULT_FONTS[platform.name()]

# The keys a theme file uses for the six things in it that are not colors.
# They sit beside "colors" rather than in it because resolve_colors drops
# every value that is not a valid QColor - and icon_color is a color that
# deliberately is not a token: it paints image files, not a stylesheet.
_OPACITY_KEY = 'opacity'
_ICONS_KEY = 'icons'
_ICON_SIZE_KEY = 'icon_size'
_ICON_COLOR_KEY = 'icon_color'
_FONT_KEY = 'font'
# The sixth non-color key. Unlike the five above it is a list of objects
# rather than a scalar, and its values are file paths that only mean
# something relative to the theme file they came from - which is why it
# does not go through _load_theme_value. See impl/background.py.
_BACKGROUNDS_KEY = 'backgrounds'

# Every color fman draws, with the values it used before themes existed.
# A token appears here iff it is referenced from styles.qss, Theme.css or
# one of the build_*palette functions below - test_themes.py enforces both
# directions, so a hex literal cannot creep back into the stylesheets.
DEFAULT_COLORS = {
	# File list
	'pane_bg': '#272822',
	'pane_fg': '#75715e',
	'pane_fg_dir': 'white',
	'pane_hidden_fg': '#9975715e',
	'pane_hidden_fg_dir': '#99ffffff',
	'pane_selected_fg': '#f92672',
	'pane_cursor_bg': '#49483e',
	'header_bg': '#363731',
	# Text
	'muted_fg': '#8f908a',
	'bright_fg': 'white',
	'readonly_fg': '#9a9a9a',
	# Chrome
	'border': '#7d7d7d',
	'input_bg': '#303030',
	'input_border': '#363731',
	'statusbar_bg_top': '#5b5b5b',
	'statusbar_bg_bottom': '#545454',
	'locationbar_border': '#262626',
	# Quicksearch popup
	'popup_bg': '#404040',
	'popup_selected_bg': '#575757',
	'popup_query_border': '#8e8e8e',
	'popup_query_inner_border': '#2c2c2c',
	'popup_input_bg': '#e6e6e6',
	'popup_input_fg': '#1d1d1d',
	'popup_input_border': '#dddddd',
	'popup_input_border_top': '#aeaeae',
	'popup_input_border_left': '#c9c9c9',
	'popup_input_border_right': '#d0d0d0',
	'popup_item_fg': '#c8c8c8',
	'popup_divider_top': '#4d4d4d',
	'popup_divider_bottom': '#363636',
	# Dims the main window while a modal dialog is open. The alpha byte is
	# how strong the dim is, so a theme needs no second key for it:
	# '#00000000' switches the scrim off entirely.
	'scrim_bg': '#80000000',
	# QPalette-only: roles Qt draws itself, which no stylesheet reaches.
	'window_bg': '#2b2b2b',
	'main_window_bg': '#444444',
	'base_bg': '#131313',
	'alt_row_bg': '#42403b',
	'button_bg': '#292929',
	'button_fg': '#b6b3ab',
	'palette_midlight': '#333333',
	'palette_mid': '#252525',
	'palette_dark': '#202020',
	'palette_shadow': '#1d1d1d'
}

def substitute(text, colors):
	"""
	Replaces $token placeholders in a QSS/CSS file's text. safe_substitute
	leaves unknown names and stray '$' untouched, so a user's own Theme.css
	can never fail to load because of a dollar sign.
	"""
	return Template(text).safe_substitute(colors)

# A theme only has to name the ~16 tokens that have no entry here; every
# other token inherits from its parent unless the theme overrides it. That
# is what keeps "write a theme" at sixteen colors instead of thirty-nine,
# and it is why `base_bg` follows `pane_bg`: a new theme cannot accidentally
# leave the text viewer (which samples QPalette.Base) on the old background.
FALLBACKS = {
	'pane_fg_dir': 'bright_fg',
	'readonly_fg': 'muted_fg',
	'input_border': 'header_bg',
	'statusbar_bg_bottom': 'statusbar_bg_top',
	'locationbar_border': 'header_bg',
	'popup_query_border': 'border',
	# These inherit `border`, never `popup_bg`: a separator that defaults to
	# the surface it sits on is invisible by construction, which turns the
	# command palette into an undifferentiated wall of text.
	'popup_query_inner_border': 'border',
	'popup_divider_top': 'border',
	'popup_divider_bottom': 'border',
	'popup_input_bg': 'input_bg',
	'popup_input_fg': 'bright_fg',
	'popup_input_border': 'border',
	'popup_input_border_top': 'popup_input_border',
	'popup_input_border_left': 'popup_input_border',
	'popup_input_border_right': 'popup_input_border',
	'base_bg': 'pane_bg',
	'main_window_bg': 'window_bg',
	'alt_row_bg': 'pane_cursor_bg',
	'button_bg': 'window_bg',
	'button_fg': 'muted_fg',
	'palette_midlight': 'header_bg',
	'palette_mid': 'button_bg',
	'palette_dark': 'button_bg',
	'palette_shadow': 'button_bg'
}

# Derive faded colors from each theme; a fixed fallback can be brighter than
# a theme's pane foreground.
_FADED = {
	'pane_hidden_fg': 'pane_fg',
	'pane_hidden_fg_dir': 'pane_fg_dir'
}
_HIDDEN_OPACITY = 0.6

# A theme's value ends up inside a QSS declaration, so anything that could
# close it turns a theme file into a stylesheet injection. The quotes are
# in here for the font family: build_tokens wraps it in double quotes, so
# that is the character which would end the string early.
_ILLEGAL_IN_VALUE = set(';{}"\n\r')

def is_valid_color(value):
	return isinstance(value, str) \
		and not _ILLEGAL_IN_VALUE & set(value) \
		and QColor(value).isValid()

def resolve_colors(theme_json):
	"""
	A theme's partial color map turned into a value for every token, via
	FALLBACKS and then DEFAULT_COLORS. Unknown tokens and invalid values are
	ignored rather than raising - a typo in a theme file must not stop fman
	from starting.
	"""
	given = {
		key: value for key, value in (theme_json.get('colors') or {}).items()
		if key in DEFAULT_COLORS and is_valid_color(value)
	}
	result = {token: _resolve(token, given) for token in DEFAULT_COLORS}
	for token, parent in _FADED.items():
		if token not in given:
			result[token] = _faded(result[parent])
	return result

def _faded(color):
	color = QColor(color)
	color.setAlphaF(color.alphaF() * _HIDDEN_OPACITY)
	return color.name(QColor.HexArgb)

def build_tokens(colors, font):
	"""
	The map Theme substitutes into styles.qss and every Theme.css: a theme's
	colors plus the one token that is not one. The family is quoted here
	rather than in the CSS so that a name with spaces cannot fall apart, and
	so there is a single place that knows the token's name.
	"""
	return dict(colors, font_family='"%s"' % font)

# What Theme substitutes when nobody has said otherwise. Every $token in
# styles.qss and the bundled Theme.css must appear here - test_themes.py
# enforces that in both directions.
DEFAULT_TOKENS = build_tokens(DEFAULT_COLORS, DEFAULT_FONT)

def _resolve(token, given):
	# Inherit from the nearest ancestor the theme actually named. If it
	# named none of them, the token keeps its own default rather than the
	# ancestor's - otherwise an empty theme would not reproduce
	# DEFAULT_COLORS, which is what makes the default look provable.
	node = token
	seen = set()
	while node is not None and node not in seen:
		if node in given:
			return given[node]
		seen.add(node)
		node = FALLBACKS.get(node)
	return DEFAULT_COLORS[token]

def list_themes(dirs):
	"""
	Theme names available in `dirs`, sorted. A theme's name is its file name
	without the extension - the same string that is shown in the command
	palette and stored in the settings, so there is no second place for it
	to disagree with.
	"""
	# The default is always offered: it needs no file (an empty JSON is
	# what it is) and must stay reachable even if `dirs` are missing.
	result = {DEFAULT_THEME}
	for dir_ in dirs:
		for path in glob(join(dir_, '*.json')):
			result.add(splitext(basename(path))[0])
	return sorted(result)

def _read_theme_json(name, dirs):
	"""
	Theme `name`'s JSON object, or {} if it does not exist or is unreadable.
	Later dirs win, so a user theme shadows a bundled one of the same name.
	Never raises: a broken theme file must not stop fman from starting.
	"""
	return _read_theme_json_with_dir(name, dirs)[0]

def _read_theme_json_with_dir(name, dirs):
	"""
	The same, plus the directory the winning file was read from (None if
	there was none). Only load_backgrounds needs the directory - it
	resolves the theme's image paths against it - but it has to be the
	*same* read: a second pass over `dirs` would be a second copy of the
	"later dirs win" rule, free to disagree with this one.
	"""
	result = {}
	result_dir = None
	for dir_ in dirs:
		try:
			with open(join(dir_, name + '.json'), 'r') as f:
				contents = json.load(f)
		except (OSError, ValueError):
			continue
		# A theme file is valid JSON without being an object: `[]` and `5`
		# parse fine and would make every .get(...) below raise. Ignore such
		# a file the way an unreadable one is ignored.
		if isinstance(contents, dict):
			result = contents
			result_dir = dir_
	return result, result_dir

def load_theme(name, dirs):
	"""
	The colors of theme `name`, or DEFAULT_COLORS if it does not exist or is
	unreadable.
	"""
	return resolve_colors(_read_theme_json(name, dirs))

def _load_theme_value(name, dirs, key, normalize):
	"""
	Theme `name`'s value for the non-color `key`, or None if it asks for
	none or asks for something unusable. One read-and-validate path for the
	five scalar ones, so a new non-color key of that shape is a key and a
	validator. `backgrounds` is not of that shape - see load_backgrounds.
	"""
	return normalize(_read_theme_json(name, dirs).get(key))

def load_opacity(name, dirs):
	"""
	The window opacity theme `name` asks for, or None if it asks for none.
	"""
	return _load_theme_value(name, dirs, _OPACITY_KEY, _normalize_opacity)

def load_icon_set_name(name, dirs):
	"""
	The icon set theme `name` asks for, or None if it asks for none. Whether
	that set exists is not decided here: load_icon_set answers that, and
	answers None for a set that is missing - the same as asking for none.
	"""
	return _load_theme_value(name, dirs, _ICONS_KEY, _normalize_icon_set_name)

def load_icon_size(name, dirs):
	"""
	The icon size theme `name` asks for, or None if it asks for none.
	"""
	return _load_theme_value(name, dirs, _ICON_SIZE_KEY, _normalize_icon_size)

def load_icon_color(name, dirs):
	"""
	The color theme `name` wants its icons recolored to, or None if it asks
	for none.
	"""
	return _load_theme_value(name, dirs, _ICON_COLOR_KEY, _normalize_icon_color)

def load_font(name, dirs):
	"""
	The font family theme `name` asks for, or None if it asks for none.
	"""
	return _load_theme_value(name, dirs, _FONT_KEY, _normalize_font)

def load_backgrounds(name, dirs):
	"""
	The images theme `name` places behind fman's UI, or an empty tuple if
	it places none - and likewise for every entry that asks for something
	unusable.

	The one non-color key that does not go through _load_theme_value: its
	validator also needs the directory the theme file was read from,
	because a theme states its image paths relative to itself.
	"""
	contents, dir_ = _read_theme_json_with_dir(name, dirs)
	return normalize_backgrounds(contents.get(_BACKGROUNDS_KEY), dir_)

def scale_icon_size(icon_size, factor):
	"""
	`icon_size` grown or shrunk by `factor`, so the icons track the pane font
	zoom (see the Core plugin's pane font size commands). factor=1.0 returns
	`icon_size` untouched - None included, which is what keeps an unzoomed
	fman asking Qt for nothing at all rather than for 16 pixels.
	"""
	if factor == 1.0:
		return icon_size
	base = DEFAULT_ICON_SIZE_PX if icon_size is None else icon_size
	return max(MIN_ICON_SIZE, min(MAX_ICON_SIZE, round(base * factor)))

def _normalize_icon_set_name(value):
	"""
	`value` as an icon set name, or None if it cannot be one. Delegates to
	fman.impl.model.icon_set so the rule that keeps a name from climbing out
	of the icon directories lives with the code that reads those directories.
	"""
	return value if is_valid_icon_set_name(value) else None

def _normalize_icon_size(value):
	"""
	`value` as an int in [MIN_ICON_SIZE, MAX_ICON_SIZE], or None if it is not
	a usable icon size. Booleans are rejected explicitly for the same reason
	as in _normalize_opacity: True is an int in Python.
	"""
	if isinstance(value, bool) or not isinstance(value, int):
		return None
	return value if MIN_ICON_SIZE <= value <= MAX_ICON_SIZE else None

def _normalize_icon_color(value):
	"""
	`value` as a color to recolor icons with, or None if it cannot be one.
	Answers to is_valid_color like every color in a theme file: this one is
	painted onto a QImage rather than into a QSS rule, but a theme file that
	can reach one can reach the other, so it clears the same bar.
	"""
	return value if is_valid_color(value) else None

def _normalize_font(value):
	"""
	`value` as a font family, or None if it cannot be one. Whether the family
	is installed is deliberately not checked - the same rule as
	is_valid_icon_set_name, which validates shape only. Qt falls back to its
	own font for a family it does not know, so a typo costs you the typeface
	rather than the ability to start fman.
	"""
	if not isinstance(value, str) or _ILLEGAL_IN_VALUE & set(value):
		return None
	return value if value.strip() else None

def _normalize_opacity(value):
	"""
	`value` as a float in [MIN_OPACITY, 1.0], or None if it is not a usable
	opacity. Shared by the theme files and the user's own setting so both
	answer to one contract. Booleans are rejected explicitly: True is an int
	in Python and would otherwise read as "fully opaque".
	"""
	if isinstance(value, bool) or not isinstance(value, (int, float)):
		return None
	result = float(value)
	return result if MIN_OPACITY <= result <= DEFAULT_OPACITY else None

def build_palette(colors):
	result = QPalette()
	result.setColor(QPalette.Window, QColor(colors['window_bg']))
	result.setColor(QPalette.WindowText, QColor(colors['bright_fg']))
	result.setColor(QPalette.Base, QColor(colors['base_bg']))
	result.setColor(QPalette.AlternateBase, QColor(colors['alt_row_bg']))
	result.setColor(QPalette.ToolTipBase, QColor(colors['base_bg']))
	result.setColor(QPalette.ToolTipText, QColor(colors['bright_fg']))
	# Qt draws the focus rectangle (view/__init__.py) in the Light role, so
	# it tracks the cursor row's background by definition:
	result.setColor(QPalette.Light, QColor(colors['pane_cursor_bg']))
	result.setColor(QPalette.Midlight, QColor(colors['palette_midlight']))
	result.setColor(QPalette.Button, QColor(colors['button_bg']))
	result.setColor(QPalette.Mid, QColor(colors['palette_mid']))
	result.setColor(QPalette.Dark, QColor(colors['palette_dark']))
	result.setColor(QPalette.Shadow, QColor(colors['palette_shadow']))
	result.setColor(QPalette.Text, QColor(colors['bright_fg']))
	result.setColor(QPalette.ButtonText, QColor(colors['button_fg']))
	result.setColor(QPalette.Link, QColor(colors['bright_fg']))
	result.setColor(QPalette.LinkVisited, QColor(colors['bright_fg']))
	# Prevent blue highlight around buttons when the window (/dialog) is in
	# the background and thus inactive:
	result.setColor(
		QPalette.Inactive, QPalette.Highlight,
		result.color(QPalette.Midlight)
	)
	return result

def build_main_window_palette(colors):
	result = QPalette(build_palette(colors))
	result.setColor(QPalette.Window, QColor(colors['main_window_bg']))
	return result

def build_progress_bar_palette(colors):
	result = QPalette(build_main_window_palette(colors))
	# On Windows, when the progress bar (/the progress dialog) is in the
	# background, ie. not the active window, its color changes from blue to
	# white. Avoid this:
	result.setColor(
		QPalette.Inactive, QPalette.Highlight,
		result.color(QPalette.Active, QPalette.Highlight)
	)
	return result
