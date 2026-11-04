"""Own the optional compact view and route pane-wide view updates."""

from fman.impl.view.compact_view import CompactFileView
from PyQt5.QtCore import QSize


class PaneViewMode:
	"""Switch a pane between its detail and compact file views."""

	def __init__(self, pane_widget, file_view, on_activated=None,
			 on_doubleclicked=None):
		self._pane_widget = pane_widget
		self._file_view = file_view
		self._compact_view = None
		self._compact = False
		self._style_sheet = ''
		self._on_activated = on_activated
		self._on_doubleclicked = on_doubleclicked

	def is_compact(self):
		return self._compact

	def visible_view(self):
		if self._compact and self._compact_view is not None:
			return self._compact_view
		return self._file_view

	def set_compact(self, compact):
		compact = bool(compact)
		if compact == self._compact:
			return
		if compact:
			self._create_compact_view()
		self._compact = compact
		self._show_active_view()
		if not compact:
			self._dispose_compact_view()

	def _create_compact_view(self):
		view = CompactFileView(self._file_view, self._on_doubleclicked)
		if self._on_activated is not None:
			view.activated.connect(self._on_activated)
		view.setModel(self._file_view.model())
		view.setSelectionModel(self._file_view.selectionModel())
		view.setIconSize(self._file_view.iconSize())
		view.setStyleSheet(self._style_sheet or self._file_view.styleSheet())
		view.set_backgrounds(
			getattr(self._file_view, '_backgrounds', ()),
			getattr(self._file_view, '_pane_index', 0)
		)
		view.set_loading(getattr(self._file_view, '_loading_text', ''))
		layout = self._pane_widget.layout()
		layout.insertWidget(layout.indexOf(self._file_view), view)
		view.hide()
		self._compact_view = view

	def _dispose_compact_view(self):
		view = self._compact_view
		if view is None:
			return
		self._pane_widget.layout().removeWidget(view)
		view.hide()
		view.deleteLater()
		self._compact_view = None

	def _show_active_view(self):
		view = self.visible_view()
		mounted = getattr(self._pane_widget, '_mounted_widget', None)
		if mounted is None:
			self._file_view.setVisible(view is self._file_view)
			if self._compact_view is not None:
				self._compact_view.setVisible(view is self._compact_view)
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
		if self._compact_view is not None:
			self._compact_view.setIconSize(icon_size)
			self._compact_view.set_grid_width()

	def set_style_sheet(self, css):
		self._style_sheet = css
		self._file_view.setStyleSheet(css)
		if self._compact_view is not None:
			self._compact_view.setStyleSheet(css)

	def set_backgrounds(self, backgrounds, pane_index):
		self._file_view.set_backgrounds(backgrounds, pane_index)
		if self._compact_view is not None:
			self._compact_view.set_backgrounds(backgrounds, pane_index)

	def set_loading(self, text):
		self._file_view.set_loading(text)
		if self._compact_view is not None:
			self._compact_view.set_loading(text)
