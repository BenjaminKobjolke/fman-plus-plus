"""Commands and listeners that act on the window rather than its files.

The window title starts with both panes' folder names and is rebuilt on every
navigation, so `_format_window_title` is a pure string builder kept apart from
the Qt access around it. The icon toggles write settings the engine owns
(`fman.impl.model.icon_provider`) and then reload the panes to redraw.
"""
from core.commands.util import is_file_url
from core.panes import reload_panes
from core.settings import get_setting, save_setting
from fman import APP_NAME, ApplicationCommand, DirectoryPaneListener, \
	PLATFORM, show_status_message
from fman.impl.model.table import invalidate_icons
# The engine owns these: it reads the settings the two icon toggles below
# write, and never imports this plugin - so the names live there.
from fman.impl.model.icon_provider import EXECUTABLE_ICONS_KEY, \
	NETWORK_ICONS_KEY, OVERLAY_ICONS_KEY, SETTINGS_FILE as ICON_SETTINGS_FILE
from fman.impl.util.qt.thread import run_in_main_thread
from fman.url import as_human_readable

__all__ = [
	'CenterWindow', 'LocationBarListener', 'Minimize', 'ToggleExecutableIcons',
	'ToggleNetworkIcons', 'ToggleOverlayIcons', 'UpdateWindowTitle'
]

_WINDOW_TITLE_SUFFIX = ' - ' + APP_NAME

def _folder_name(path):
	trimmed = path.rstrip('\\/')
	if not trimmed or not any(
		separator in trimmed for separator in ('\\', '/')
	):
		return path
	return trimmed[max(trimmed.rfind('\\'), trimmed.rfind('/')) + 1:]

def _format_window_title(paths):
	# Pure string builder, kept separate from the pane/Qt access so it's
	# unit-testable without a running application.
	names = [_folder_name(path) for path in paths if path]
	if not names:
		return APP_NAME
	return ' | '.join(names) + _WINDOW_TITLE_SUFFIX

def _path_for_title(pane):
	try:
		return as_human_readable(pane.get_path())
	except Exception:
		# Some locations (e.g. 'null://') can't be turned into a human
		# path. Skip them rather than let the title update crash.
		return ''

@run_in_main_thread
def _refresh_window_title(window):
	paths = [_path_for_title(pane) for pane in window.get_panes()]
	window._widget.setWindowTitle(_format_window_title(paths))

class UpdateWindowTitle(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# Set the initial title when fman starts (mirrors InitPaneFontSize),
		# then keep it in sync as either pane navigates.
		_refresh_window_title(self.pane.window)
	def on_path_changed(self):
		_refresh_window_title(self.pane.window)

class Minimize(ApplicationCommand):
	aliases = ('Minimize to taskbar',)

	def __call__(self):
		self.window.minimize()

class CenterWindow(ApplicationCommand):

	aliases = ('Center window',)

	def __call__(self):
		self.window.center_on_screen()

def _is_showing_icons(key):
	return get_setting(ICON_SETTINGS_FILE, key, False)

class _ToggleIconSetting(ApplicationCommand):

	# Underscore-prefixed so `from .window import *` skips it: the plugin
	# loader registers every class reachable from `core`, and a base class
	# is not a command anyone should be able to bind a key to.
	_SETTING_KEY = None

	def __call__(self):
		show_real_icons = not _is_showing_icons(self._SETTING_KEY)
		# None clears the key so the file doesn't carry the default around:
		save_setting(
			ICON_SETTINGS_FILE, self._SETTING_KEY, show_real_icons or None
		)
		invalidate_icons()
		reload_panes(self.window)

class ToggleNetworkIcons(_ToggleIconSetting):

	aliases = ('Toggle network drive icons',)

	_SETTING_KEY = NETWORK_ICONS_KEY

class ToggleExecutableIcons(_ToggleIconSetting):

	# An icon set draws every .exe the same. The OS icon says *which*
	# program it is, which is worth more in a folder full of them - so this
	# opts .exe and .lnk back out of the active icon set.
	aliases = ('Toggle real icons for programs and shortcuts',)

	_SETTING_KEY = EXECUTABLE_ICONS_KEY

class ToggleOverlayIcons(_ToggleIconSetting):

	aliases = ('Toggle overlay icons',)

	_SETTING_KEY = OVERLAY_ICONS_KEY

class LocationBarListener(DirectoryPaneListener):
	def on_location_bar_clicked(self):
		url = self.pane.get_path()
		if is_file_url(url):
			path = as_human_readable(url)
			self.pane.run_command('go_to', {'query': path})
			ctrl = 'Cmd' if PLATFORM == 'Mac' else 'Ctrl'
			show_status_message(
				'Hint: You can also press %s+P to open GoTo. If you merely '
				'want to copy the current path, close GoTo, then press '
				'Backspace followed by F11.' % ctrl, timeout_secs=15
			)
