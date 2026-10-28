from . import clipboard
from .url import dirname
from .impl.task import StubProgressDialog, ChildProgressDialog
from .impl.console_log import format_log_args, get_console_log
from .impl.incognito import is_incognito
from .impl.portable import portable_data_directory
from .impl.view.pane_mount import get_colors, mount_widget, unmount_widget
from contextlib import contextmanager
from fbs_runtime import platform
from os import getenv
from os.path import join, expanduser
from PyQt5.QtWidgets import QMessageBox

import re

__all__ = [
	'ApplicationCommand', 'DirectoryPaneCommand', 'DirectoryPaneListener',
	'Viewer', 'find_viewer', 'viewer_for_category',
	'load_json', 'save_json',
	'show_alert', 'show_prompt', 'show_status_message', 'clear_status_message',
	'show_file_open_dialog',
	'show_quicksearch', 'QuicksearchItem',
	'get_application_commands', 'run_application_command',
	'log',
	'get_application_command_aliases', 'load_plugin', 'unload_plugin',
	'is_incognito',
	'get_themes', 'get_theme', 'set_theme',
	'get_window_opacity', 'set_window_opacity',
	'clipboard',
	'submit_task', 'Task',
	'PLATFORM', 'FMAN_VERSION', 'APP_NAME', 'DATA_DIRECTORY',
	'OK', 'CANCEL', 'YES', 'NO', 'YES_TO_ALL', 'NO_TO_ALL', 'ABORT', 'RETRY'
]

YES = QMessageBox.Yes
NO = QMessageBox.No
YES_TO_ALL = QMessageBox.YesToAll
NO_TO_ALL = QMessageBox.NoToAll
ABORT = QMessageBox.Abort
RETRY = QMessageBox.Retry
OK = QMessageBox.Ok
CANCEL = QMessageBox.Cancel

FMAN_VERSION = ''

# Keep this in sync with display_name in src/build/settings/base.json.
APP_NAME = 'fman++'

PLATFORM = platform.name()

if PLATFORM == 'Windows':
	_DEFAULT_DATA_DIRECTORY = join(getenv('APPDATA'), 'fman')
elif PLATFORM == 'Mac':
	_DEFAULT_DATA_DIRECTORY = expanduser('~/Library/Application Support/fman')
elif PLATFORM == 'Linux':
	_DEFAULT_DATA_DIRECTORY = expanduser('~/.config/fman')

# FMAN_DATA_DIRECTORY points settings, plugins and caches at a different
# profile. Demo recordings use it for a throwaway one, so a run neither loads
# the developer's third-party plugins (their key bindings would win over
# Core's, and their commands would change what the palette resolves a query to)
# nor writes viewer zoom/volume back into the real profile. A marked portable
# build otherwise keeps its profile beside the executable.
DATA_DIRECTORY = (
	getenv('FMAN_DATA_DIRECTORY')
	or portable_data_directory()
	or _DEFAULT_DATA_DIRECTORY
)

class ApplicationCommand:
	def __init__(self, window):
		self.window = window
	def __call__(self, *args, **kwargs):
		raise NotImplementedError()
	@property
	def aliases(self):
		return re.sub(r'([a-z])([A-Z])', r'\1 \2', self.__class__.__name__) \
				.lower().capitalize(),

def _set_path_onerror(e, url):
	if isinstance(e, FileNotFoundError):
		return dirname(url)
	raise

class DirectoryPane:
	def __init__(self, window, widget, command_registry):
		self.window = window
		self._widget = widget
		self._command_registry = command_registry
		self._listeners = []
		self._get_file_under_cursor_orig = self.get_file_under_cursor

	def _add_listener(self, listener):
		self._listeners.append(listener)
	def _broadcast(self, event, *args):
		for listener in self._listeners:
			getattr(listener, event)(*args)

	def get_commands(self):
		return self._command_registry.get_commands()
	def get_viewer_commands(self):
		return self._command_registry.get_viewer_commands()
	def _rewrite_command(self, name, args):
		while True:
			for listener in self._listeners:
				rewritten = listener.on_command(name, args)
				if rewritten:
					name, args = rewritten
					break
			else:
				break
		return name, args
	def run_command(self, name, args=None):
		if args is None:
			args = {}
		name, args = self._rewrite_command(name, args)
		return self._command_registry.execute_command(name, args, self)
	def get_command_aliases(self, command_name):
		return self._command_registry.get_command_aliases(command_name)
	def is_command_visible(self, command_name):
		return self._command_registry.is_command_visible(command_name, self)

	def _add_filter(self, filter_):
		self._widget.add_filter(filter_)
	def _set_dimmer(self, dimmer):
		self._widget.set_dimmer(dimmer)
	def _remove_filter(self, filter_):
		self._widget.remove_filter(filter_)

	def get_selected_files(self):
		return self._widget.get_selected_files()
	def get_file_under_cursor(self):
		return self._widget.get_file_under_cursor()
	def move_cursor_down(self, toggle_selection=False):
		self._widget.move_cursor_down(toggle_selection)
	def move_cursor_up(self, toggle_selection=False):
		self._widget.move_cursor_up(toggle_selection)
	def move_cursor_home(self, toggle_selection=False):
		self._widget.move_cursor_home(toggle_selection)
	def move_cursor_end(self, toggle_selection=False):
		self._widget.move_cursor_end(toggle_selection)
	def move_cursor_page_down(self, toggle_selection=False):
		self._widget.move_cursor_page_down(toggle_selection)
	def move_cursor_page_up(self, toggle_selection=False):
		self._widget.move_cursor_page_up(toggle_selection)
	def place_cursor_at(self, file_url):
		self._widget.place_cursor_at(file_url)
	# TODO: Rename to get_location()
	def get_path(self):
		return self._widget.get_location()
	# TODO: Rename to set_location(...)
	def set_path(self, dir_url, callback=None, onerror=_set_path_onerror):
		args = dir_url, '', True
		while True:
			for listener in self._listeners:
				rewritten = listener.before_location_change(*args)
				if rewritten and rewritten != args:
					args = rewritten
					break
			else:
				break
		self._widget.set_location(args[0], args[1], args[2], callback, onerror)
	def reload(self):
		self._widget.reload()
	def edit_name(self, file_url, selection_start=0, selection_end=None):
		self._widget.edit_name(file_url, selection_start, selection_end)
	def select_all(self):
		self._widget.select_all()
	def clear_selection(self):
		self._widget.clear_selection()
	def toggle_selection(self, file_url):
		self._widget.toggle_selection(file_url)
	def select(self, file_urls):
		self._widget.select(file_urls, ignore_errors=True)
	def deselect(self, file_urls):
		self._widget.deselect(file_urls, ignore_errors=True)
	def focus(self):
		self._widget.focus()
	def mount_widget(self, view, focus=True):
		"""
		Shows `view` in this pane in place of its file list. The pane's key
		handling is the widget's own from then on - fman only puts it there.
		Call unmount_widget() to bring the file list back.

		focus=False mounts without grabbing keyboard focus, so the pane the
		command ran from stays focused (see "View file in other pane").
		"""
		mount_widget(self, self._widget, view, focus)
	def unmount_widget(self):
		unmount_widget(self._widget)
	def get_mounted_widget(self):
		return self._widget._mounted_widget
	def show_status_message(self, text, timeout_secs=None):
		"""Show a message for this pane, optionally clearing it after a timeout."""
		return self.window._widget.show_pane_status_message(
			self._widget, text, timeout_secs)
	def clear_status_message(self):
		"""Clear this pane's message without removing another pane's message."""
		return self.window._widget.clear_pane_status_message(self._widget)
	def get_colors(self):
		"""
		This pane's live (background, foreground) as hex strings. Mounted
		widgets should paint with these rather than hardcoding colors, so
		they follow the active theme.
		"""
		return get_colors(self._widget)
	def get_columns(self):
		return self._widget.get_columns()
	def set_sort_column(self, column, ascending=True):
		self._widget.set_sort_column(column, ascending)
	def get_sort_column(self):
		return self._widget.get_sort_column()
	def _has_focus(self):
		return self._widget.hasFocus()
	@contextmanager
	def _override_file_under_cursor(self, value):
		self.get_file_under_cursor = lambda: value
		yield
		self.get_file_under_cursor = self._get_file_under_cursor_orig

class Window:
	def __init__(self, widget, panecmd_registry):
		self._widget = widget
		self._panecmd_registry = panecmd_registry
		self._panes = []
	def get_panes(self):
		return self._panes
	def minimize(self):
		self._widget.minimize()
	def center_on_screen(self):
		self._widget.center_on_screen()
	def add_pane(self):
		pane_widget = self._widget.add_pane()
		pane = DirectoryPane(self, pane_widget, self._panecmd_registry)
		self._panes.append(pane)
		_get_controller().register_pane(pane_widget, pane)
		return pane
	def remove_pane(self, pane):
		"""Remove a pane; indices to its right shift down by one."""
		if len(self._panes) < 2:
			raise ValueError('Cannot remove the last pane.')
		if pane not in self._panes:
			raise ValueError('Pane does not belong to this window.')
		if pane.get_mounted_widget() is not None:
			pane.unmount_widget()
		self._panes.remove(pane)
		_get_controller().unregister_pane(pane._widget, pane)
		self._widget.remove_pane(pane._widget)

class DirectoryPaneCommand:
	# True promises the command acts on the viewed file, its folder, or layout;
	# stays understandable with the list hidden; leaves viewer and Qt keys free;
	# and has no viewer-specific equivalent. Subclasses inherit this flag.
	usable_in_viewer = False

	def __init__(self, pane):
		self.pane = pane
	def __call__(self, *args, **kwargs):
		raise NotImplementedError()
	def is_visible(self):
		return True
	def get_chosen_files(self):
		selected_files = self.pane.get_selected_files()
		if selected_files:
			return selected_files
		file_under_cursor = self.pane.get_file_under_cursor()
		if file_under_cursor:
			return [file_under_cursor]
		return []

class Viewer:

	"""
	Shows a file inside a DirectoryPane, in place of its file list. Subclass
	this in a plugin and fman's "View file" will use it for the files your
	matches() claims - see docs/viewers/PLUGIN_VIEWERS.md.
	"""

	# Unique and stable. It is also the category next/previous-file navigation
	# uses and the key this viewer's own settings are stored under, so
	# renaming it silently resets those settings.
	name = ''

	# Decides between two viewers that both match a url. Registration order is
	# plugin load order, which is not a useful priority - Core's text viewer
	# matches anything text-like and sits at -100 so plugins get first refusal.
	priority = 0

	def matches(self, url):
		return False

	def show(self, pane, url, focus_view=True):
		"""
		Build your widget and hand it to pane.mount_widget(). focus_view=False
		means mount it without taking keyboard focus - the user is viewing
		into the other pane and wants to keep browsing in this one.
		"""
		raise NotImplementedError()

class DirectoryPaneListener:
	def __init__(self, pane):
		self.pane = pane
	def on_activated(self):
		pass
	def on_doubleclicked(self, file_url):
		pass
	def on_name_edited(self, file_url, new_name):
		pass
	# TODO: Rename to after_location_change()
	def on_path_changed(self):
		pass
	def before_location_change(self, url, sort_column='', ascending=True):
		pass
	def on_files_dropped(self, file_urls, dest_dir, is_copy_not_move):
		pass
	def on_command(self, command_name, args):
		pass
	def on_location_bar_clicked(self):
		pass
	def on_incognito_changed(self, enabled):
		pass

def load_json(name, default=None, save_on_quit=False):
	return _get_plugin_support().load_json(name, default, save_on_quit)

def save_json(name, value=None):
	return _get_plugin_support().save_json(name, value)

def show_alert(text, buttons=OK, default_button=OK):
	return _get_ui().show_alert(text, buttons, default_button)

def log(*args):
	get_console_log().append(format_log_args(*args))

def show_prompt(text, default='', selection_start=0, selection_end=None):
	return _get_ui().show_prompt(text, default, selection_start, selection_end)

def show_status_message(text, timeout_secs=None):
	return _get_ui().show_status_message(text, timeout_secs)

def clear_status_message():
	return _get_ui().clear_status_message()

def show_file_open_dialog(caption, dir_path, filter_text=''):
	return _get_ui().show_file_open_dialog(caption, dir_path, filter_text)

def show_quicksearch(
	get_items, get_tab_completion=None, query='', item=0, alt_accept=False
):
	return _get_ui().show_quicksearch(
		get_items, get_tab_completion, query, item, alt_accept
	)

class QuicksearchItem:
	def __init__(
		self, value, title=None, highlight=None, hint='', description=''
	):
		if title is None:
			title = value
		if highlight is None:
			highlight = []
		self.value = value
		self.title = title
		self.highlight = highlight
		self.hint = hint
		self.description = description
	def __repr__(self):
		return '<%s: %s>' % (self.__class__.__name__, self.title)

def get_application_commands():
	return _get_plugin_support().get_application_commands()

def run_application_command(name, args=None):
	if args is None:
		args = {}
	return _get_plugin_support().run_application_command(name, args)

def get_application_command_aliases(command_name):
	return _get_plugin_support().get_application_command_aliases(command_name)

def find_viewer(url):
	"""
	The Viewer that handles `url`, or None if none does. Highest priority
	wins; see fman.Viewer and docs/viewers/PLUGIN_VIEWERS.md.
	"""
	return _get_app_ctxt().viewer_registry.find(url)

def viewer_for_category(name):
	"""
	The Viewer registered under `name`, or None. For code that has a stored
	category rather than a url.
	"""
	return _get_app_ctxt().viewer_registry.for_category(name)

def get_themes():
	"""
	The names of the available color themes, sorted. See docs/THEMES.md.
	"""
	return _get_app_ctxt().theme_controller.get_themes()

def get_theme():
	"""
	The name of the currently active color theme.
	"""
	return _get_app_ctxt().theme_controller.get_theme()

def set_theme(name):
	"""
	Applies the color theme `name` immediately and remembers it across
	restarts. An unknown name falls back to fman's default colors.
	"""
	return _get_app_ctxt().theme_controller.set_theme(name)

def get_window_opacity():
	"""
	How opaque fman's window currently is, from 0.3 to 1.0. This is the
	user's own setting if they have one, else what the active theme asks
	for, else 1.0.
	"""
	return _get_app_ctxt().theme_controller.get_opacity()

def set_window_opacity(value):
	"""
	Applies opacity `value` (0.3 - 1.0) immediately and remembers it across
	restarts. Pass None to forget it and follow the active theme again.
	Raises ValueError for a number outside the supported range.
	"""
	return _get_app_ctxt().theme_controller.set_opacity(value)

def get_icon_sets():
	"""
	The names of the available icon sets, sorted. "System" means the icons
	the operating system supplies. See docs/THEMES.md.
	"""
	return _get_app_ctxt().theme_controller.get_icon_sets()

def get_icon_set():
	"""
	The name of the icon set the file list currently draws. This is the
	user's own setting if they have one, else what the active theme asks
	for, else "System".
	"""
	return _get_app_ctxt().theme_controller.get_icon_set()

def set_icon_set(name):
	"""
	Applies the icon set `name` and remembers it across restarts. Pass None
	to forget it and follow the active theme again. Panes still show the
	icons they loaded under the old set until they are reloaded.
	"""
	return _get_app_ctxt().theme_controller.set_icon_set(name)

def get_fonts():
	"""
	The font families fman can draw in, sorted. This is everything Qt
	knows: the families fman bundles and the ones the operating system
	supplies. See docs/THEMES.md.
	"""
	return _get_app_ctxt().theme_controller.get_fonts()

def get_font():
	"""
	The font family the UI is currently drawn in. This is the user's own
	setting if they have one, else what the active theme asks for, else
	fman's default for this platform.
	"""
	return _get_app_ctxt().theme_controller.get_font()

def set_font(name):
	"""
	Draws the UI in font family `name` and remembers it across restarts.
	Pass None to forget it and follow the active theme again. A family
	this machine does not have falls back to Qt's own font.
	"""
	return _get_app_ctxt().theme_controller.set_font(name)

def get_icon_size():
	"""
	How big the file list draws its icons, in pixels, or None when neither
	the user nor the theme asks for a size and Qt's own default applies.
	"""
	return _get_app_ctxt().theme_controller.get_icon_size()

def set_icon_size(value):
	"""
	Applies icon size `value` (12 - 64 pixels) immediately and remembers it
	across restarts. Pass None to forget it and follow the active theme
	again. Raises ValueError for a size outside the supported range.
	"""
	return _get_app_ctxt().theme_controller.set_icon_size(value)

def set_icon_scale(factor):
	"""
	Scales the drawn icon size by `factor`, so the icons follow a font zoom.
	Unlike set_icon_size this is not remembered: whatever decides `factor`
	is expected to be saved and re-applied itself. 1.0 means no scaling.
	"""
	return _get_app_ctxt().theme_controller.set_icon_scale(factor)

def set_palette_font_scale(factor):
	"""
	Scales the command palette's font sizes by `factor`, so it follows a font
	zoom. Like set_icon_scale this is not remembered: whatever decides
	`factor` is expected to be saved and re-applied itself. 1.0 means no
	scaling.
	"""
	return _get_app_ctxt().theme_controller.set_palette_font_scale(factor)

def get_icon_color():
	"""
	The color the file list's icon set is recolored to, or None when neither
	the user nor the theme asks for one and the icons keep their own colors.
	"""
	return _get_app_ctxt().theme_controller.get_icon_color()

def set_icon_color(value):
	"""
	Recolors the icon set's icons to `value` - any color Qt understands -
	and remembers it across restarts. Pass None to forget it and follow the
	active theme again. Raises ValueError for a color fman cannot use. Only
	an icon set answers to this; the OS icons cannot be recolored. Panes
	still show the icons they loaded until they are reloaded.
	"""
	return _get_app_ctxt().theme_controller.set_icon_color(value)

def load_plugin(plugin_path):
	return _get_plugin_support().load_plugin(plugin_path)

def unload_plugin(plugin_path):
	"""
	Raises ValueError if the plugin was not loaded.
	"""
	_get_plugin_support().unload_plugin(plugin_path)

class Task:

	class Canceled(KeyboardInterrupt):
		pass

	# When Copy or Move run tasks on several workers (see
	# FileSystem#get_parallel_transfers): a task that waits for earlier tasks,
	# e.g. deleting a folder emptied by a move, starts once they are all done.
	# One that blocks later tasks, e.g. creating a folder, keeps them from
	# starting until it is done. Class attributes, not arguments, so a plugin
	# can set them on an instance and still load in an older fman.
	waits_for_earlier_tasks = False
	blocks_later_tasks = False
	keeps_focus = False
	minimizable = False
	icon = None

	def __init__(self, title, size=0, fn=lambda: None, args=(), kwargs=None):
		if kwargs is None:
			kwargs = {}
		self._title = title
		self._fn = fn
		self._args = args
		self._kwargs = kwargs
		self._size = size
		self._dialog = StubProgressDialog()
	def __call__(self):
		self._fn(*self._args, **self._kwargs)
	def get_title(self):
		return self._title
	def set_text(self, text):
		self._dialog.set_text(text)
	def set_size(self, size):
		self._size = size
		self._dialog.set_task_size(size)
	def get_size(self):
		return self._size
	def set_progress(self, progress):
		self._dialog.set_progress(progress)
	def get_progress(self):
		return self._dialog.get_progress()
	def check_canceled(self):
		if self._dialog.was_canceled():
			raise self.Canceled()
	def run(self, subtask):
		self.set_text(subtask.get_title())
		self._run_with_dialog(subtask, ChildProgressDialog(self._dialog))
	def _run_with_dialog(self, subtask, dialog):
		subtask._dialog = dialog
		subtask()
		# Some tasks, especially those with size 1, may not "complete" their
		# progress at the end. Do it for them:
		subtask.set_progress(subtask.get_size())
	def show_alert(self, *args, **kwargs):
		return self._dialog.show_alert(*args, **kwargs)
	def show_workers(self, workers):
		"""
		Lists the parallel workers in the progress dialog, with buttons to add
		and remove them. `workers` provides snapshot(), add(), remove(),
		can_add() and can_remove(), like core's TransferWorkers. It may also
		provide connection_count(), the number shown beside the thread count,
		or None when the count is unknown.
		"""
		self._dialog.show_workers(workers)
	def __str__(self):
		return self._title

def submit_task(task):
	from fman.impl.tool_windows import ToolWindowOptions
	options = ToolWindowOptions.of(task)
	dialog = _get_ui().create_progress_dialog(
		task.get_title(), task.get_size(), options
	)
	dialog_before = task._dialog
	task._dialog = dialog
	try:
		task()
	except Task.Canceled:
		pass
	finally:
		dialog.cancel()
		task._dialog = dialog_before

def _get_plugin_support():
	return _get_app_ctxt().plugin_support

def _get_controller():
	return _get_app_ctxt().controller

def _get_ui():
	return _get_app_ctxt().main_window

def _get_app_ctxt():
	from fman.impl.application_context import get_application_context
	return get_application_context()
