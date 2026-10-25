"""
Swapping a widget into a DirectoryPane in place of its (hidden) file list, and
taking it back out again. This is what the built-in file viewers are built on
(the Core plugin's core/textviewer.py, imageviewer.py, videoviewer.py), and
what DirectoryPane.mount_widget/unmount_widget expose to plugins so they can
put their own widget in a pane without a file behind it.

Lives here rather than in the Core plugin because it is engine behaviour: it
knows DirectoryPaneWidget's layout, its file view and its focus proxy. It
deliberately knows nothing about what is being mounted - a viewer's own
concerns (an unsaved-edit prompt, say) stay with that viewer.
"""
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPalette

def get_colors(pane_widget):
	"""
	The pane's live (background, foreground) as hex strings, read off the file
	view's palette so a mounted widget matches whatever theme is active
	instead of hardcoding colors of its own.
	"""
	palette = pane_widget._file_view.palette()
	return (
		palette.color(QPalette.Base).name(),
		palette.color(QPalette.Text).name()
	)

def mount_widget(pane, pane_widget, view, focus=True):
	"""
	Swaps `view` into the pane's layout in place of the (hidden) file list.

	focus=False mounts the widget without grabbing keyboard focus - used when
	mounting into the *other* pane (ViewFileInOtherPane), so the pane the
	command ran from stays focused for continued browsing.
	"""
	# Keep the pane status line last so it stays at the bottom while mounted
	# viewers and plugin widgets take the file list's place.
	pane_widget.layout().insertWidget(
		pane_widget.layout().count() - 1, view)
	pane_widget._file_view.setVisible(False)
	pane_widget._mounted_widget = view
	# Re-point the pane's focus proxy at the mounted widget. switch_panes()
	# ends by calling the *other* pane's focus(), which is setFocus() on this
	# pane's widget - following the proxy. Without this it would land back on
	# the hidden file view instead of the widget when tabbing back. Set even
	# when not grabbing focus now, so tabbing into this pane later lands on
	# the widget rather than the hidden file list.
	pane_widget.setFocusProxy(view)
	if focus:
		# The command palette's modal dialog restores focus to the (now
		# hidden) file view as it closes, right before this function runs.
		# Grabbing focus here immediately gets clobbered by that restore, so
		# the caret never shows. Defer one event-loop tick so we focus after
		# it settles:
		QTimer.singleShot(0, view.setFocus)
	else:
		# Mounting into the *other* pane: keep focus on the pane the command
		# ran from (the opposite of this target pane) so browsing continues
		# there. Just skipping the setFocus above isn't enough - mounting
		# still blurs the source pane's file list - so actively re-focus it,
		# on the same deferred tick, to win over that blur.
		panes = pane.window.get_panes()
		source = panes[(panes.index(pane) + 1) % len(panes)]
		QTimer.singleShot(0, source.focus)

@run_in_main_thread
def unmount_widget(pane_widget):
	view = pane_widget._mounted_widget
	if view is None:
		return
	pane_widget.layout().removeWidget(view)
	view.deleteLater()
	pane_widget._mounted_widget = None
	# Restore the pane's original focus proxy (set in DirectoryPaneWidget
	# .__init__) before the file view reclaims focus.
	pane_widget.setFocusProxy(pane_widget._file_view)
	pane_widget._file_view.setVisible(True)
	pane_widget._file_view.setFocus()
