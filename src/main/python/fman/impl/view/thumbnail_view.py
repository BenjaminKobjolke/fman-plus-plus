"""Icon-grid view that displays asynchronously loaded file previews."""

from bisect import bisect_left
from fman.impl.view.compact_view import CompactFileView
from fman.impl.view.thumbnail_cache import ThumbnailCache
from fman.impl.view.thumbnail_delegate import ThumbnailDelegate
from fman.impl.view.thumbnail_settings import ThumbnailSettings
from PyQt5.QtCore import QSize, Qt


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
		rows = self._visible_rows(model.rowCount())
		if not rows:
			return
		self._file_view.request_rows(rows)
		urls = [model.url(model.index(row, 0)) for row in rows]
		self._thumbnail_cache.request(urls)

	def _visible_rows(self, count: int) -> list[int]:
		model = self.model()
		height = self.viewport().height()

		def rect(row):
			return self.visualRect(model.index(row, 0))

		# Centred icons are smaller than their grid cells, so cell-corner probes
		# miss them.
		first = bisect_left(
			range(count), True, key=lambda row: rect(row).bottom() >= 0
		)
		rows = []
		row = first
		while row < count:
			item_rect = rect(row)
			if item_rect.top() >= height:
				break
			if item_rect.isValid():
				rows.append(row)
			row += 1
		return rows

	def set_grid_width(self, *_):
		self._update_grid_size()

	def _thumbnail_ready(self, url):
		model = self.model()
		if model is None:
			return
		try:
			index = model.find(url)
		except (ValueError, KeyError):
			return
		self.viewport().update(self.visualRect(index))
