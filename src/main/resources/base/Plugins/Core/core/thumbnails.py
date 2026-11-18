"""Core settings and zoom behavior for fman's thumbnail pane view."""
from core.imageviewer import IMAGE_EXTENSIONS
from core.settings import SETTINGS_FILE, get_setting, save_setting
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.view.thumbnail_settings import (
	LOCATIONS_EVERYWHERE, LOCATIONS_LOCAL, MAX_SIZE, MIN_SIZE,
	PREVIEWS_IMAGES, PREVIEWS_WINDOWS, ThumbnailSettings,
)

PREVIEWS_KEY = 'thumbnail_previews'
LOCATIONS_KEY = 'thumbnail_locations'
SIZE_KEY = 'thumbnail_size'

DEFAULT_PREVIEWS = PREVIEWS_IMAGES
DEFAULT_LOCATIONS = LOCATIONS_LOCAL
DEFAULT_SIZE = 128


def get_thumbnail_settings():
	previews = get_setting(SETTINGS_FILE, PREVIEWS_KEY)
	if previews not in (
			PREVIEWS_IMAGES,
			PREVIEWS_WINDOWS):
		previews = DEFAULT_PREVIEWS

	locations = get_setting(SETTINGS_FILE, LOCATIONS_KEY)
	if locations not in (
			LOCATIONS_LOCAL,
			LOCATIONS_EVERYWHERE):
		locations = DEFAULT_LOCATIONS

	size = get_setting(SETTINGS_FILE, SIZE_KEY)
	if not isinstance(size, int) or isinstance(size, bool):
		size = DEFAULT_SIZE
	else:
		size = max(MIN_SIZE, min(MAX_SIZE, size))

	return ThumbnailSettings(
		size=size,
		previews=previews,
		locations=locations,
		image_extensions=IMAGE_EXTENSIONS,
	)


def step_size(size, delta):
	size = round(size * (1.25 ** delta))
	return max(MIN_SIZE, min(MAX_SIZE, size))


def change_thumbnail_size(window, delta):
	settings = get_thumbnail_settings()
	size = step_size(settings.size, delta)
	save_setting(SETTINGS_FILE, SIZE_KEY, size)
	settings = ThumbnailSettings(
		size=size,
		previews=settings.previews,
		locations=settings.locations,
		image_extensions=settings.image_extensions,
	)
	_apply_to_thumbnail_panes(window, settings)
	return size


@run_in_main_thread
def _apply_to_thumbnail_panes(window, settings):
	for pane in window.get_panes():
		if pane.is_thumbnail_view():
			pane._widget.set_thumbnail_settings(settings)
