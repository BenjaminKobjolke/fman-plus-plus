"""Own the optional compact or thumbnail view and route pane-wide updates."""

from fman.impl.view.compact_view import CompactFileView
from fman.impl.view.thumbnail_settings import ThumbnailSettings
from fman.impl.view.thumbnail_view import ThumbnailFileView
from PyQt5.QtCore import QSize


class PaneViewMode:
	"""Switch a pane between details, compact, and thumbnail file views."""

	DETAILS = 'details'
	COMPACT = 'compact'
	THUMBNAILS = 'thumbnails'

	def __init__(self, pane_widget, file_view, on_activated=None,
			 on_doubleclicked=None):
		self._pane_widget = pane_widget
		self._file_view = file_view
		self._alt_view = None
		self._mode = self.DETAILS
		self._thumbnail_settings = ThumbnailSettings()
		self._style_sheet = ''
		self._on_activated = on_activated
		self._on_doubleclicked = on_doubleclicked

	def is_compact(self):
		return self._mode == self.COMPACT

	def is_thumbnails(self):
		return self._mode == self.THUMBNAILS

	def visible_view(self):
		if self._mode != self.DETAILS and self._alt_view is not None:
			return self._alt_view
		return self._file_view

	def set_compact(self, compact):
		if compact:
			self.set_mode(self.COMPACT)
		elif self.is_compact():
			self.set_mode(self.DETAILS)

	def set_thumbnails(self, thumbnails):
		if thumbnails:
			self.set_mode(self.THUMBNAILS)
		elif self.is_thumbnails():
			self.set_mode(self.DETAILS)

	def set_thumbnail_settings(self, settings):
		self._thumbnail_settings = settings
		if self.is_thumbnails() and self._alt_view is not None:
			self._alt_view.set_thumbnail_settings(settings)

	def set_mode(self, mode):
		if mode not in (self.DETAILS, self.COMPACT, self.THUMBNAILS):
			raise ValueError('Unsupported pane view mode: %s' % mode)
		if mode == self._mode:
			return

		old_view = self._alt_view
		if mode == self.DETAILS:
			self._mode = mode
			self._alt_view = None
			self._show_active_view()
			self._dispose_view(old_view)
			return

		new_view = self._create_view(mode)
		self._alt_view = new_view
		self._mode = mode
		self._show_active_view()
		self._dispose_view(old_view)

	def _create_view(self, mode):
		if mode == self.COMPACT:
			view = CompactFileView(self._file_view, self._on_doubleclicked)
		else:
			view = ThumbnailFileView(self._file_view,
									 on_doubleclicked=self._on_doubleclicked)
		if self._on_activated is not None:
			view.activated.connect(self._on_activated)
		view.setModel(self._file_view.model())
		view.setSelectionModel(self._file_view.selectionModel())
		if mode == self.COMPACT:
			view.setIconSize(self._file_view.iconSize())
		else:
			view.set_thumbnail_settings(self._thumbnail_settings)
		view.setStyleSheet(self._style_sheet or self._file_view.styleSheet())
		view.set_backgrounds(
			getattr(self._file_view, '_backgrounds', ()),
			getattr(self._file_view, '_pane_index', 0)
		)
		view.set_loading(getattr(self._file_view, '_loading_text', ''))
		layout = self._pane_widget.layout()
		layout.insertWidget(layout.indexOf(self._file_view), view)
		view.hide()
		return view

	def _dispose_view(self, view):
		if view is None:
			return
		self._pane_widget.layout().removeWidget(view)
		view.hide()
		view.deleteLater()

	def _show_active_view(self):
		view = self.visible_view()
		mounted = getattr(self._pane_widget, '_mounted_widget', None)
		if mounted is None:
			self._file_view.setVisible(view is self._file_view)
			if self._alt_view is not None:
				self._alt_view.setVisible(view is self._alt_view)
			self._set_focus_proxy(view)

	def _set_focus_proxy(self, view):
		self._pane_widget.setFocusProxy(view)
		location_bar = getattr(self._pane_widget, '_location_bar', None)
		if location_bar is not None:
			location_bar.setFocusProxy(view)

	def hide(self):
		"""Hide the current file view while a viewer is mounted."""
		self.visible_view().setVisible(False)

	def restore(self):
		"""Restore whichever file view is active after a viewer is unmounted."""
		self._show_active_view()

	def set_icon_size(self, size):
		icon_size = QSize() if size is None else QSize(size, size)
		self._file_view.setIconSize(icon_size)
		if self.is_compact() and self._alt_view is not None:
			self._alt_view.setIconSize(icon_size)
			self._alt_view.set_grid_width()

	def set_style_sheet(self, css):
		self._style_sheet = css
		self._file_view.setStyleSheet(css)
		if self._alt_view is not None:
			self._alt_view.setStyleSheet(css)

	def set_backgrounds(self, backgrounds, pane_index):
		self._file_view.set_backgrounds(backgrounds, pane_index)
		if self._alt_view is not None:
			self._alt_view.set_backgrounds(backgrounds, pane_index)

	def set_loading(self, text):
		self._file_view.set_loading(text)
		if self._alt_view is not None:
			self._alt_view.set_loading(text)
