from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QStyledItemDelegate


class ThumbnailDelegate(QStyledItemDelegate):
	"""Draw a cached preview while retaining the file-view delegate behavior."""

	def __init__(self, view, cache, base_delegate):
		super().__init__(view)
		self._view = view
		self._cache = cache
		self._base_delegate = base_delegate

	def paint(self, painter, option, index):
		model = index.model()
		pixmap = None
		if hasattr(model, 'url'):
			pixmap = self._cache.get(model.url(index))
		self._base_delegate.paint(painter, option, index)
		if pixmap is not None:
			target = QRect(
				option.rect.center().x() - pixmap.width() // 2,
				option.rect.top() + 4,
				pixmap.width(),
				pixmap.height(),
			)
			painter.drawPixmap(target, pixmap)

	def initStyleOption(self, option, index):
		self._base_delegate.initStyleOption(option, index)

	def helpEvent(self, event, view, option, index):
		return self._base_delegate.helpEvent(event, view, option, index)

	def createEditor(self, parent, option, index):
		return self._base_delegate.createEditor(parent, option, index)

	def eventFilter(self, editor, event):
		return self._base_delegate.eventFilter(editor, event)
