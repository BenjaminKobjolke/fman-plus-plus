from fman.impl.util.qt import ClickFocus, WA_MacShowFocusRect
from fman.impl.view.location_segments import location_segments, segment_at
from fman.url import as_human_readable
from PyQt5.QtCore import QPoint, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QPainter, QPalette
from PyQt5.QtWidgets import QLineEdit

class LocationBar(QLineEdit):

	clicked = pyqtSignal()
	segment_clicked = pyqtSignal(str)

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setFocusPolicy(ClickFocus)
		self.setAttribute(WA_MacShowFocusRect, 0)
		self.setReadOnly(True)
		self.setMouseTracking(True)
		self._segments = []
		self._clickable = True
		self._hovered_segment = None
	def set_location(self, url: str) -> None:
		self.setText(as_human_readable(url))
		self._segments = location_segments(url)
		self._hovered_segment = None
		self.update()
	def set_clickable(self, enabled: bool) -> None:
		self._clickable = enabled
		if not enabled:
			self._hovered_segment = None
		self.setCursor(Qt.ArrowCursor)
		self.update()
	def mousePressEvent(self, e):
		segment = None
		if self._clickable and e.button() == Qt.LeftButton:
			segment = segment_at(self._segments, self.cursorPositionAt(e.pos()))
		super().mousePressEvent(e)
		if segment is None:
			self.clicked.emit()
		else:
			self.segment_clicked.emit(segment.url)
	def mouseMoveEvent(self, e):
		segment = None
		if self._clickable:
			segment = segment_at(self._segments, self.cursorPositionAt(e.pos()))
		super().mouseMoveEvent(e)
		self._hovered_segment = segment
		self.setCursor(
			Qt.PointingHandCursor if segment is not None else Qt.ArrowCursor
		)
		self.update()
	def leaveEvent(self, e):
		self._hovered_segment = None
		self.unsetCursor()
		self.update()
		super().leaveEvent(e)
	def paintEvent(self, e):
		super().paintEvent(e)
		if self._hovered_segment is None:
			return
		contents = self.contentsRect()
		visible_start = self.cursorPositionAt(
			QPoint(contents.left() + 1, contents.center().y())
		)
		start = max(visible_start, 0)
		end = self._hovered_segment.end
		if start >= end:
			return
		left = contents.left()
		width = self.fontMetrics().horizontalAdvance(self.text()[start:end])
		color = QColor(self.palette().color(QPalette.Highlight))
		color.setAlpha(70)
		painter = QPainter(self)
		painter.fillRect(left, contents.top(), width, contents.height(), color)
