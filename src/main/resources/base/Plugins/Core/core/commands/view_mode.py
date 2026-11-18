from fman import DirectoryPaneCommand
from fman import DirectoryPaneListener
from fman.impl.util.qt.thread import run_in_main_thread
from core.thumbnails import get_thumbnail_settings

__all__ = [
	'InitThumbnailView', 'ToggleCompactView', 'ToggleThumbnailView'
]


class ToggleCompactView(DirectoryPaneCommand):
	aliases = ('Toggle compact view',)

	@run_in_main_thread
	def __call__(self):
		widget = self.pane._widget
		widget.set_compact_view(not widget.is_compact_view())


class ToggleThumbnailView(DirectoryPaneCommand):
	aliases = ('Toggle thumbnail view',)

	@run_in_main_thread
	def __call__(self):
		widget = self.pane._widget
		enabled = not widget.is_thumbnail_view()
		if enabled:
			widget.set_thumbnail_settings(get_thumbnail_settings())
		widget.set_thumbnail_view(enabled)


class InitThumbnailView(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.pane._widget.set_thumbnail_settings(get_thumbnail_settings())
