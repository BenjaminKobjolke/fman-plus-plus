"""
File-change watching for the text viewer (core/textviewer.py) - auto-reload
and tail mode. Split out of core/textviewer.py to stay under the project's
300-line file cap. Like core/textviewer_reload.py, the toggle/start/stop/
on_file_changed functions operate directly on the PaneTextView instance
(`view`) passed in - see core/textviewer_pane.py's confirm_close for the
same pattern.
"""
from core.textviewer_reload import reload_from_disk, scroll_to_end
from core.viewer_status import viewer_status
import os

from PyQt5.QtCore import QFileSystemWatcher

def start_watch(path, on_changed, parent):
	"""
	Watches `path` and calls `on_changed()` (no args) whenever it changes.
	`parent` should be the QObject that owns the watcher's lifetime (e.g. the
	viewer widget), so the watcher is destroyed automatically when its parent
	is - no separate teardown needed. Returns the QFileSystemWatcher, or None
	if path is falsy.
	"""
	if not path:
		return None
	watcher = QFileSystemWatcher([path], parent)
	def _handle(_changed_path):
		# Many editors save via atomic rename (write temp file, rename over
		# the original), which drops the watched path from Qt's watch list -
		# re-add it so subsequent saves keep firing.
		if os.path.exists(path) and path not in watcher.files():
			watcher.addPath(path)
		on_changed()
	watcher.fileChanged.connect(_handle)
	return watcher

def toggle_auto_reload(view):
	if view._watcher is not None and not view._tail:
		stop_auto_reload(view)
	else:
		start_auto_reload(view, tail=False)

def toggle_tail(view):
	if view._watcher is not None and view._tail:
		stop_auto_reload(view)
	else:
		start_auto_reload(view, tail=True)

def reload_actions(view):
	"""Palette rows for file watching, or none for text without a file."""
	if view._path is None:
		return []
	watching = view._watcher is not None
	auto_label = (
		'Disable auto-reload' if watching and not view._tail
		else 'Enable auto-reload'
	)
	tail_label = (
		'Disable tail mode' if watching and view._tail
		else 'Enable tail mode (follow end)'
	)
	return [
		(auto_label, lambda: toggle_auto_reload(view), '', 'text_toggle_auto_reload'),
		(tail_label, lambda: toggle_tail(view), '', 'text_toggle_tail'),
	]

def _watch_view(view):
	return start_watch(view._path, lambda: on_file_changed(view), view)

def rewatch(view):
	"""
	Re-points an active watcher at view._path, for when the file is renamed
	under it (core/viewer_file_ops.py) - QFileSystemWatcher watches the path,
	not the file. A no-op when nothing is being watched.
	"""
	if view._watcher is None:
		return
	view._watcher.deleteLater()
	view._watcher = _watch_view(view)

def start_auto_reload(view, tail):
	if view._watcher is None:
		view._watcher = _watch_view(view)
	view._tail = tail
	viewer_status(view._nav.pane, 'Tail mode on' if tail else 'Auto-reload on')
	if tail:
		scroll_to_end(view)

def stop_auto_reload(view):
	view._watcher.deleteLater()
	view._watcher = None
	view._tail = False
	viewer_status(view._nav.pane, 'Auto-reload off')

def on_file_changed(view):
	if view._editing and view.document().isModified():
		viewer_status(view._nav.pane, 'File changed on disk (not reloaded)')
		return
	if not os.path.exists(view._path):
		return  # Transient during an atomic save (temp file not yet renamed).
	reload_from_disk(view, tail=view._tail)
