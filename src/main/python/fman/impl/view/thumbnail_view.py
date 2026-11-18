"""Icon-grid view that displays asynchronously loaded file previews."""

from fman.impl.view.compact_view import CompactFileView
from fman.impl.view.thumbnail_cache import ThumbnailCache
from fman.impl.view.thumbnail_delegate import ThumbnailDelegate
from fman.impl.view.thumbnail_settings import ThumbnailSettings
from PyQt5.QtCore import QPoint, QSize, Qt


class ThumbnailFileView(CompactFileView):
	"""A pane view sharing the file list's model and selection model."""

	GRID_PADDING = 24

	def __init__(self, file_view, cache=None, on_doubleclicked=None):
		super().__init__(file_view, on_doubleclicked)
		self._thumbnail_cache = cache or ThumbnailCache(
			ThumbnailSettings(), parent=self
		)
		self._thumbnail_delegate = ThumbnailDelegate(
			self, self._thumbnail_cache, self._composite_delegate
		)
		self.setItemDelegate(self._thumbnail_delegate)
		self._thumbnail_cache.ready.connect(self._thumbnail_ready)
		self.setViewMode(self.IconMode)
		self.setFlow(self.LeftToRight)
		self.setWrapping(True)
		self.setResizeMode(self.Adjust)
		self.setMovement(self.Static)
		self.setUniformItemSizes(True)
		self.setWordWrap(True)
		self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.setTextElideMode(Qt.ElideMiddle)
		self.set_thumbnail_settings(self._thumbnail_cache._settings)

	def set_thumbnail_settings(self, settings: ThumbnailSettings):
		self._thumbnail_cache.set_settings(settings)
		self.setIconSize(QSize(settings.size, settings.size))
		self._update_grid_size()
		self.viewport().update()

	def _update_grid_size(self):
		metrics = self.fontMetrics()
		width = self.iconSize().width() + self.GRID_PADDING
		height = self.iconSize().height() + metrics.height() * 2 + 12
		self.setGridSize(QSize(width, height))

	def _request_visible_rows(self):
		model = self.model()
		if model is None or not model.rowCount():
			return
		rect = self.viewport().rect()
		grid = self.gridSize()
		rows = set()
		for x in range(0, rect.width(), max(1, grid.width())):
			for y in range(0, rect.height(), max(1, grid.height())):
				index = self.indexAt(QPoint(x + 1, y + 1))
				if index.isValid():
					rows.add(index.row())
		if not rows:
			return
		rows = sorted(rows)
		self._file_view.request_rows(rows)
		urls = [model.url(model.index(row, 0)) for row in rows]
		self._thumbnail_cache.request(urls)

	def _thumbnail_ready(self, url):
		model = self.model()
		if model is None:
			return
		try:
			index = model.find(url)
		except (ValueError, KeyError):
			return
		self.viewport().update(self.visualRect(index))

	def resizeEvent(self, event):
		super().resizeEvent(event)
		self._update_grid_size()
