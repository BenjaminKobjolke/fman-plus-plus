"""
Reload-from-disk for the text viewer (core/textviewer.py): the scroll/cursor-
preserving reload used by manual Revert, and the scroll-to-end variant used by
tail mode (core/textviewer_watch.py). Split out of core/textviewer.py to stay
under the project's 300-line file cap.

Like core/textviewer_pane.py's confirm_close, these operate directly on the
PaneTextView instance (`view`) passed in rather than staying fully decoupled -
the reload sequence is inherently tied to that widget's private state
(`_path`/`_editable`/`_editing`/`_set_read_only`).
"""
from core.textviewer_io import load_for_view
from core.viewer_status import viewer_status
from PyQt5.QtGui import QTextCursor

def set_text_preserving_scroll(view, text):
	vpos = view.verticalScrollBar().value()
	cpos = view.textCursor().position()
	view.setPlainText(text)
	view.document().setModified(False)
	cursor = view.textCursor()
	# Clamp: the file may have shrunk since cpos was captured.
	cursor.setPosition(min(cpos, len(view.toPlainText())))
	view.setTextCursor(cursor)
	view.verticalScrollBar().setValue(vpos)

def scroll_to_end(view):
	view.moveCursor(QTextCursor.End)
	scrollbar = view.verticalScrollBar()
	scrollbar.setValue(scrollbar.maximum())

def reload_from_disk(view, tail):
	"""
	Shared by manual reload (PaneTextView._revert) and auto-reload
	(core.textviewer_watch.on_file_changed): loads `view._path`, updates
	`_editable`, replaces the text (preserving scroll, or jumping to the end
	if `tail`), and falls back to read-only if editing is no longer supported.

	Returns whether that fallback happened - losing edit mode is the one
	outcome worth reporting over the caller's own status message, so callers
	report theirs only when this is False (see PaneTextView._revert).
	"""
	text, editable = load_for_view(view._path)
	view._editable = editable
	text = view._format.display(text)
	if tail:
		view.setPlainText(text)
		view.document().setModified(False)
		scroll_to_end(view)
	else:
		set_text_preserving_scroll(view, text)
	if view._editing and not view._editable:
		view._editing = False
		view._set_read_only()
		viewer_status(view._nav.pane, 'File no longer editable - now read-only')
		return True
	return False
