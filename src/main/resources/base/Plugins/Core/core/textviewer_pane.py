"""
Pane-mounting glue for the text viewer (core/textviewer.py): the caret-fix
stylesheet and the unsaved-edit confirmation prompt. Split out of
core/textviewer.py to stay under the project's 300-line file cap — genuinely
separate from PaneTextView itself (the widget/editor behaviour) even though
both are Qt-touching.

The swapping itself now lives in the engine (fman/impl/view/pane_mount.py,
exposed as DirectoryPane.mount_widget/unmount_widget) so plugins can mount
their own widgets too. mount_view/close_view below are shims kept for the
callers — and any plugin — that already use them.
"""
from fman import show_alert, YES, NO, CANCEL, translate
from fman.localization_keys import SAVE_CHANGES_BEFORE_CLOSING
from fman.impl.view.pane_mount import unmount_widget

# Once the app-wide Theme.css ("* { font-size: ...pt; }", applied via
# QApplication.setStyleSheet) touches a widget, Qt switches that widget from
# palette-based rendering to the QSS style engine — and the QSS engine only
# draws the blinking text caret if `color`/`background-color` are set
# explicitly; otherwise it silently stops drawing it. This mirrors the same
# wildcard-rule problem the font-size feature works around for the file list
# (`FileListView { font-size: ...pt; }`, commands/pane_view.py) — a local
# type-selector override wins over the global `*` rule. `bg`/`fg` are read
# from the live file view's palette (see begin_new_view) so the viewer
# always matches the pane colors, whatever theme set them. `font_size`, when
# given, is the viewer's own zoom override (see PaneTextView._apply_font_size)
# — folded into the same local rule so it likewise beats the wildcard `*` rule.
def caret_fix_css(bg, fg, font_size=None):
	css = 'QPlainTextEdit { color: %s; background-color: %s;' % (fg, bg)
	if font_size is not None:
		css += ' font-size: %dpt;' % font_size
	return css + ' }'

def confirm_close(view):
	"""
	If `view` is mid-edit with unsaved changes, asks to save/discard/cancel.
	Returns True if it's fine to proceed with closing or replacing the view
	(nothing unsaved, or the user just saved/discarded), False if the caller
	must abort (user cancelled). Shared by PaneTextView._exit_with_dirty_check
	and begin_new_view(), which otherwise would silently drop unsaved edits
	when a second view replaces the currently open buffer. Also shared by
	non-text views (e.g. PaneImageView, core/imageviewer.py) that have no
	`_editing`/`document()` of their own - getattr's False default short-
	circuits before `document()` is ever called on them, so they always
	report safe to close.
	"""
	if not (getattr(view, '_editing', False) and view.document().isModified()):
		return True
	answer = show_alert(
		translate(SAVE_CHANGES_BEFORE_CLOSING), YES | NO | CANCEL, YES
	)
	if answer & CANCEL:
		return False
	if answer & YES:
		view._save()
	return True

def begin_new_view(pane):
	"""
	Confirms/discards any existing viewer in this pane's widget, then returns
	(widget, bg, fg) for constructing the replacement PaneTextView. Returns
	None if the user cancelled a save/discard prompt for unsaved edits
	already open in this pane, in which case the caller must not replace it.
	Shared by show_text_viewer and show_text_in_viewer (core/textviewer.py).
	"""
	existing_view = pane.get_mounted_widget()
	if existing_view is not None and not confirm_close(existing_view):
		# User cancelled out of the save/discard prompt for the view
		# currently open in this pane — leave it open, don't replace it.
		return None
	pane.unmount_widget()
	bg, fg = pane.get_colors()
	return pane._widget, bg, fg

def mount_view(pane, widget, view, focus_view=True):
	"""
	Shim over DirectoryPane.mount_widget, kept because the three viewers (and
	any plugin that reached in here before the pane API existed) call it with
	the (pane, widget) pair begin_new_view hands back. `widget` is redundant
	now - the pane knows its own - and is ignored.
	"""
	pane.mount_widget(view, focus=focus_view)

def close_view(pane_widget):
	"""
	Shim over DirectoryPane.unmount_widget for callers that hold the pane
	*widget* rather than the pane - which is what every viewer's on_close
	callback captures (see core/imageviewer.py:194).
	"""
	unmount_widget(pane_widget)
