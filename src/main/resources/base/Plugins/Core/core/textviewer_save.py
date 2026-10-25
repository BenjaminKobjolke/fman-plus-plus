"""
Writing the text viewer's buffer back to disk (core/textviewer.py: the Save
file / Save file as… palette entries). Split out of core/textviewer.py to stay
under the project's 300-line file cap.

Like core/textviewer_reload.py - its counterpart in the other direction -
these operate directly on the PaneTextView instance (`view`) passed in, since
saving is tied to that widget's private state (`_path`/`_url`) as much as to
its buffer.
"""
from core.viewer_status import viewer_status
from fman import show_prompt
from fman.fs import notify_file_changed

def write_view(view, path):
	"""
	Writes the buffer to `path`. Returns whether it got there: a read-only
	file or a missing directory raises OSError from a palette action, where an
	uncaught one would surface as a traceback rather than as something the user
	can act on - and would leave them believing the save happened.
	"""
	# QPlainTextEdit normalizes all line endings to '\n', so a file originally
	# using CRLF is rewritten with LF on save — a known, accepted limitation
	# (see docs/views/TEXT_VIEWER.md).
	try:
		with open(path, 'wb') as f:
			f.write(view.toPlainText().encode('utf-8'))
	except OSError as e:
		viewer_status(view._nav.pane, 'Could not save: %s' % (e.strerror or e))
		return False
	return True

def _persist(view, path, message):
	# A failed write already said why, and leaves the buffer modified so the
	# edit can be retried with Save file as… - so stop here rather than
	# claiming a save that didn't happen.
	if not write_view(view, path):
		return
	view._path = path
	notify_file_changed(view._url)
	view.document().setModified(False)
	viewer_status(view._nav.pane, message)

def save(view):
	_persist(view, view._path, 'Saved')

def save_as(view):
	new_path, ok = show_prompt('Save as (full path):', default=view._path)
	if not ok or not new_path:
		return
	_persist(view, new_path, 'Saved as %s' % new_path)
