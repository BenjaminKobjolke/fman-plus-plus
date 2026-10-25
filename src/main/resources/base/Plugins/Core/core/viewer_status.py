"""
The pane status line every in-pane viewer reports through - the text, image
and video viewers (core/textviewer.py, core/imageviewer.py,
core/videoviewer.py) and their helper modules. A viewer action that changes
something the user cannot otherwise see (a reload of an unchanged file,
entering edit mode, a zoom step) confirms it here; see
docs/viewers/FILE_VIEWERS.md.

Its own module rather than a function in core/viewer_navigation.py because the
zoom modules import it too, and viewer_navigation.py already carries an import
cycle with core/viewers.py (see _category there). It only depends on the pane
API, so it adds no imports from the broader fman package.
"""
# A short timeout keeps a message from describing an old action after the
# pane's viewer changes; each pane has its own message slot.
_TIMEOUT_SECS = 3

def viewer_status(pane, text):
	pane.show_status_message(text, timeout_secs=_TIMEOUT_SECS)
