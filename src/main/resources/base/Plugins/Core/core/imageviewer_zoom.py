"""
Scale zoom for the image viewer (core/imageviewer.py) - mirrors
core/textviewer_zoom.py's font-size zoom but for a multiplicative scale
factor rather than a font point size. Reuses zoom_delta_for from
core.textviewer_zoom instead of duplicating it - the keystroke-matching
logic ("does this key event match the user's increase/decrease shortcut")
is generic, not text-viewer-specific.

change_image_scale/reset_image_scale take the settings read/write as
injectable get_saved/save parameters (defaulting to this module's own
get_saved_scale/save_scale) so the step+clamp math is unit-testable without
touching real settings I/O - see core/tests/test_imageviewer_zoom.py.
"""
from core.settings import get_setting, save_setting
from core.viewer_status import viewer_status

_SETTING_KEY = 'image_viewer_zoom'
MIN_SCALE = 0.1
MAX_SCALE = 10.0
SCALE_STEP = 1.25

def get_saved_scale():
	return get_setting('Core Settings.json', _SETTING_KEY)

def save_scale(scale):
	# scale=None clears the override (fit mode) - mirrors save_view_font_size.
	save_setting('Core Settings.json', _SETTING_KEY, scale)

def clamp_scale(scale):
	return max(MIN_SCALE, min(MAX_SCALE, scale))

def zoom_message(scale):
	# One formatter so PaneImageView._actual_size, which sets 1.0 directly
	# rather than through change_image_scale, still says it the same way.
	return 'Zoom %d%%' % round(scale * 100)

def change_image_scale(
	view, apply_scale, delta, get_saved=get_saved_scale, save=save_scale
):
	base = get_saved()
	if base is None:
		# Nothing saved yet (fit mode): step from what's actually on screen
		# right now, not a hardcoded 1.0 - otherwise zooming in on a small
		# fitted image would jump straight to 1.25x instead of stepping up
		# from its current fit scale. Mirrors effective_view_font_size.
		base = view.effective_scale()
	new_scale = clamp_scale(base * (SCALE_STEP ** delta))
	save(new_scale)
	apply_scale(new_scale)
	viewer_status(view._nav.pane, zoom_message(new_scale))

def reset_image_scale(view, apply_scale, save=save_scale):
	save(None)
	apply_scale(None)
	viewer_status(view._nav.pane, 'Fit to window')
