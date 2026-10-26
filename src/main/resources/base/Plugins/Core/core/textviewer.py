"""
A minimal text viewer/editor shown inside a directory pane, in place of the
file list. Triggered by the "View file" command (see core/commands/opening.py
- ViewFile) via show_text_viewer(pane, url), which reads `url` from disk.
Enter/double-click still open files with the OS default app; this is a
separate, palette-only path. Opens read-only; a viewer-scoped command palette
(Ctrl+Shift+P, see PaneTextView) can switch it to editable for files that are
safe to write back (see core.textviewer_io.is_editable). show_text_in_viewer
is a read-only sibling that mounts arbitrary text with no backing file - see
core/commands/release_notes.py and docs/views/RELEASE_NOTES.md.
"""
from core.key_bindings import (
	dispatch_bindable_command, KEY_BINDINGS_FILE, VIEWER_KEY_BINDINGS_FILE,
)
from core.textviewer_cursor import ViewerCursor
from core.textviewer_format import ViewerFormat
from core.textviewer_highlight import ViewerSyntax
from core.textviewer_io import MAX_VIEW_BYTES as _MAX_VIEW_BYTES, load_for_view
from core.textviewer_pane import (
	caret_fix_css, confirm_close, begin_new_view, mount_view,
	close_view as close_text_viewer,
)
from core.textviewer_reload import reload_from_disk
from core.textviewer_save import save as save_view, save_as as save_view_as
from core.textviewer_search import ViewerSearch
from core.textviewer_watch import (
	rewatch, reload_actions, toggle_auto_reload, toggle_tail,
)
from core.textviewer_zoom import (
	get_saved_view_font_size, change_view_font_size, reset_view_font_size,
	zoom_actions, zoom_delta_for, RESET_COMMAND,
)
from core.viewer_navigation import open_viewer_palette, ViewerNavigator
from core.viewer_status import viewer_status
from fman import show_alert, YES, NO, load_json
from fman.impl.util.qt.key_event import QtKeyEvent
from fman.impl.util.qt.thread import run_in_main_thread
from fman.url import as_human_readable
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPlainTextEdit

class PaneTextView(QPlainTextEdit):
	def __init__(self, on_close, on_switch, pane, bg, fg, path, url, editable):
		super().__init__()
		self._on_close = on_close
		self._on_switch = on_switch
		self._nav = ViewerNavigator(pane, 'text', on_close, self._on_renamed)
		self._search = ViewerSearch(self)
		self._cursor_keys = ViewerCursor(self)
		self._bg = bg
		self._fg = fg
		self._path = path
		self._url = url
		self._format = ViewerFormat(self)
		self._syntax = ViewerSyntax(self, bg)
		self._editable = editable
		self._editing = False
		self._watcher = None
		self._tail = False
		self._set_read_only()
		self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
		self.setStyleSheet(caret_fix_css(bg, fg, get_saved_view_font_size()))
	def keyPressEvent(self, event):
		if (event.key() == Qt.Key_P and event.modifiers() & Qt.ControlModifier
				and event.modifiers() & Qt.ShiftModifier):
			# Own palette, not fman's global Ctrl+Shift+P: the global one
			# only fires on the (now hidden) file list, and this one should
			# list viewer-only actions anyway.
			self._open_palette()
			return
		key_event = QtKeyEvent(event.key(), event.modifiers())
		key_bindings = load_json(KEY_BINDINGS_FILE, default=[])
		zoom_delta = zoom_delta_for(key_event, key_bindings)
		if zoom_delta is not None:
			# Whatever the user has increase/decrease pane font size bound
			# to (default Alt+Up/Down) also zooms the viewer - works in both
			# view and edit mode, and is checked before the edit-mode
			# passthrough below so it never gets typed into the buffer.
			change_view_font_size(self, self._apply_font_size, zoom_delta)
			return
		# Checked before the edit-mode passthrough (same reasoning as zoom
		# above) so e.g. a user-bound Ctrl+S works while typing; unbound
		# keys still fall through to normal typing. Viewer pseudo-commands
		# are looked up in their own file, separate from the zoom binding
		# above - see core.key_bindings.VIEWER_KEY_BINDINGS_FILE.
		viewer_bindings = load_json(VIEWER_KEY_BINDINGS_FILE, default=[])
		if dispatch_bindable_command(
			key_event, viewer_bindings, self._bindable_commands()
		):
			return
		if self._editing:
			# Edit mode: everything, including Tab, goes to the editor as
			# normal typing. Exit/save/switch-panes are palette-only while
			# editing, so an accidental keystroke can't discard/lose focus.
			super().keyPressEvent(event)
			return
		if self._search.handle_key(event):
			# "/", n/N and - only while searching - Escape. Before the close
			# keys below, so Escape leaves search mode before it closes.
			return
		if self._cursor_keys.handle_key(key_event):
			# Home/End/PgUp/PgDown defaults (core/textviewer_cursor.py).
			return
		if event.key() in (
			Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Backspace
		):
			self._on_close()
			return
		if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
			# Forward to the pane's own Tab binding (switch_panes) instead of
			# letting QPlainTextEdit swallow it for focus traversal. The
			# viewer stays open; show_text_viewer() re-points the pane's
			# focus proxy at us, so tabbing back re-focuses this view.
			self._on_switch()
			return
		# Viewer keys above win; only unclaimed keys reach pane commands.
		if self._url is None or not self._nav.run_pane_shortcut(key_event):
			super().keyPressEvent(event)

	def _bindable_commands(self):
		# Viewer-only pseudo-commands this focused view matches against
		# Viewer Key Bindings.json itself (see keyPressEvent) - not registered
		# DirectoryPaneCommands, not in Core's own Key Bindings.json. Mirrors
		# _get_actions's mode split so a bound key does the same thing its
		# palette entry does. viewer_switch_panes is deliberately absent in
		# edit mode - Tab must keep typing normally there (see keyPressEvent).
		if self._editing:
			commands = {
				'text_save': lambda: save_view(self),
				'text_save_as': lambda: save_view_as(self),
				'text_revert': self._revert,
				'viewer_close': self._exit_with_dirty_check,
				'viewer_open_palette': self._open_palette,
				'text_toggle_syntax_colors': self._syntax.toggle_syntax_colors,
			}
		else:
			commands = {
				'text_edit': self._enter_edit_mode,
				'text_reload': self._revert,
				'viewer_close': self._on_close,
				'viewer_switch_panes': self._on_switch,
				'viewer_open_palette': self._open_palette,
				'text_toggle_pretty': self._format.toggle_pretty,
				'text_toggle_syntax_colors': self._syntax.toggle_syntax_colors,
			}
			if self._path is not None:
				commands['text_toggle_auto_reload'] = lambda: toggle_auto_reload(self)
				commands['text_toggle_tail'] = lambda: toggle_tail(self)
			if self._url is not None:
				commands.update(self._nav.commands())
		# Both modes: a bound key is dispatched before the edit-mode
		# passthrough, so e.g. Ctrl+F keeps searching while typing, and a
		# Ctrl+Home of your own still jumps to the top. Zoom in/out need no
		# entry here - they follow the pane font-size shortcut, matched
		# earlier by zoom_delta_for; only Reset ships no key at all.
		commands.update(self._search.commands())
		commands.update(self._cursor_keys.commands())
		commands[RESET_COMMAND] = \
			lambda: reset_view_font_size(self, self._apply_font_size)
		return commands

	@run_in_main_thread
	def _on_renamed(self, new_url):
		# Unlike the image and video viewers, this one keeps addressing its
		# file by path after loading it - Save would otherwise write the
		# buffer back under the old name. Same bookkeeping Save as… does
		# (core/textviewer_save.py). Marshalled onto the main thread because
		# the rename itself runs off it (core/viewer_file_ops.py) and rewatch
		# builds a QFileSystemWatcher.
		self._url = new_url
		self._path = as_human_readable(new_url)
		self._syntax._highlighter.set_path(self._path)
		rewatch(self)

	def _apply_font_size(self, size):
		# Passed as the apply_size callback to core.textviewer_zoom, which
		# stays PyQt/stylesheet-agnostic; size=None clears the override.
		self.setStyleSheet(caret_fix_css(self._bg, self._fg, size))

	def _open_palette(self):
		open_viewer_palette(self._get_actions)

	def _get_actions(self):
		key_bindings = load_json(KEY_BINDINGS_FILE, default=[])
		watch_actions = reload_actions(self)
		zoom = zoom_actions(self, self._apply_font_size, key_bindings)
		if self._editing:
			mode_actions = [
				('Save file', lambda: save_view(self), '', 'text_save'),
				('Save file as…', lambda: save_view_as(self), '', 'text_save_as'),
				(
					'Revert / reload from disk', self._revert, '',
					'text_revert'
				),
			] + watch_actions + self._syntax.actions() + zoom + [
				(
					'Exit viewer', self._exit_with_dirty_check, '',
					'viewer_close'
				),
			]
		else:
			# Navigation is view-mode only (this branch), and only for a real
			# backing file - show_text_in_viewer mounts text with url=None
			# (release notes), where directory navigation is meaningless.
			# Mirrors the self._path gate on reload_actions.
			nav_actions = self._nav.actions() if self._url is not None else []
			mode_actions = [
				('Exit viewer', self._on_close, '', 'viewer_close'),
				('Edit file', self._enter_edit_mode, '', 'text_edit'),
				('Reload from disk', self._revert, '', 'text_reload'),
			] + watch_actions + self._format.actions() \
				+ self._syntax.actions() + zoom + nav_actions
		# Listed in both modes (core/textviewer_cursor.py, _search.py).
		return mode_actions + self._cursor_keys.actions() \
			+ self._search.actions()

	def _enter_edit_mode(self):
		if not self._editable:
			show_alert(
				"This file can't be edited here: it's either larger than "
				'%d MB or not valid UTF-8 text.'
				% (_MAX_VIEW_BYTES // (1024 * 1024))
			)
			return
		# n/N type literally once editing - stop advertising them.
		self._search.exit()
		self._editing = True
		self.setReadOnly(False)
		self.setTextInteractionFlags(Qt.TextEditorInteraction)
		self._syntax.set_editing(True)
		message = (
			'Edit mode (pretty-printed - Save reformats the file)'
			if self._format.is_pretty() else 'Edit mode'
		)
		viewer_status(self._nav.pane, message)

	def _revert(self):
		if self._editing and self.document().isModified():
			if not show_alert(
				'Discard unsaved changes and reload from disk?', YES | NO, NO
			) & YES:
				return
		if not reload_from_disk(self, tail=False):
			viewer_status(self._nav.pane, 'Reloaded from disk')

	def _exit_with_dirty_check(self):
		if confirm_close(self):
			self._on_close()

	def _set_read_only(self):
		self.setReadOnly(True)
		# setReadOnly(True) alone leaves the cursor unable to move at all via
		# the keyboard in this Qt build (verified: Right/Shift+Right are
		# silently no-ops without this) — not just editing-disabled, as the
		# name implies. Explicit flags restore keyboard navigation/selection
		# while keeping the widget non-editable. Shared by __init__ and
		# _revert (a reload that turns out non-editable falls back here too).
		self.setTextInteractionFlags(
			Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse
		)

def _mount_new_view(pane, text, path, url, editable, focus_view=True):
	# Shared by show_text_viewer/show_text_in_viewer below - both build a
	# PaneTextView the same way and only differ in what they pass in.
	prepared = begin_new_view(pane)
	if prepared is None:
		return
	widget, bg, fg = prepared
	view = PaneTextView(
		lambda: close_text_viewer(widget),
		lambda: pane.run_command('switch_panes'),
		pane, bg, fg, path, url, editable,
	)
	view.setPlainText(view._format.display(text))
	mount_view(pane, widget, view, focus_view=focus_view)

@run_in_main_thread
def show_text_viewer(pane, url, focus_view=True):
	path = as_human_readable(url)
	text, editable = load_for_view(path)
	_mount_new_view(pane, text, path, url, editable, focus_view=focus_view)

@run_in_main_thread
def show_text_in_viewer(pane, text):
	"""
	Shows arbitrary read-only text in the pane's viewer widget, with no
	backing file — used by the "Release Notes" command (core/commands/
	release_notes.py) to render a release's notes without writing a temp
	file. Always read-only (there's nothing to save back to), unlike
	show_text_viewer where editability depends on the source file.
	"""
	_mount_new_view(pane, text, None, None, False)
