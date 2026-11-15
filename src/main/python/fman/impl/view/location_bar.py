from fman.impl.util.qt import ClickFocus, WA_MacShowFocusRect
from fman.impl.path_shortening import shorten_path
from fman.impl.view.location_segments import location_segments, segment_at
from fman.url import as_human_readable
from PyQt5.QtCore import QEvent, QPoint, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QPainter, QPalette
from PyQt5.QtWidgets import QLineEdit, QMenu


# QLineEdit keeps a small inset between its content rect and displayed text.
_LINE_EDIT_MARGIN = 2

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
		self._full_text = ''
		self._shortened = None
		self._clickable = True
		self._hovered_segment = None
		self._hovered_hidden_range = None
	def set_location(self, url: str) -> None:
		self._full_text = as_human_readable(url)
		self.setToolTip(self._full_text)
		self._segments = location_segments(url)
		self._hovered_segment = None
		self._hovered_hidden_range = None
		self._apply_shortening()
	def _apply_shortening(self) -> None:
		if not hasattr(self, '_full_text'):
			return
		contents = self.contentsRect()
		margins = self.textMargins()
		available_width = (
			contents.width() - margins.left() - margins.right()
			- 2 * _LINE_EDIT_MARGIN
		)
		font_metrics = self.fontMetrics()

		def fits(text: str) -> bool:
			return font_metrics.horizontalAdvance(text) <= available_width

		self._shortened = shorten_path(
			self._full_text, fits
		)
		self.setText(
			self._shortened.text if self._shortened is not None else self._full_text
		)
		self.update()
	def resizeEvent(self, e):
		super().resizeEvent(e)
		self._apply_shortening()
	def changeEvent(self, e):
		super().changeEvent(e)
		if e.type() == QEvent.FontChange:
			self._apply_shortening()
	def set_clickable(self, enabled: bool) -> None:
		self._clickable = enabled
		if not enabled:
			self._hovered_segment = None
			self._hovered_hidden_range = None
		self.setCursor(Qt.ArrowCursor)
		self.update()
	def mousePressEvent(self, e):
		segment = None
		if self._clickable and e.button() == Qt.LeftButton:
			shown_position = self.cursorPositionAt(e.pos())
			hidden = self._hidden_at(shown_position)
			if hidden is not None:
				segments = self._hidden_segments(hidden)
				super().mousePressEvent(e)
				if segments:
					self._show_hidden_menu(segments, e.pos())
					return
			segment = segment_at(
				self._segments, self._original_index(shown_position)
			)
		super().mousePressEvent(e)
		if segment is None:
			self.clicked.emit()
		else:
			self.segment_clicked.emit(segment.url)
	def mouseMoveEvent(self, e):
		segment = None
		hidden = None
		if self._clickable:
			shown_position = self.cursorPositionAt(e.pos())
			hidden = self._hidden_at(shown_position)
			if hidden is None:
				segment = segment_at(
					self._segments, self._original_index(shown_position)
				)
			elif not self._hidden_segments(hidden):
				hidden = None
		super().mouseMoveEvent(e)
		self._hovered_segment = segment
		self._hovered_hidden_range = hidden
		self.setCursor(
			Qt.PointingHandCursor
			if segment is not None or hidden is not None else Qt.ArrowCursor
		)
		self.update()
	def _original_index(self, shown_position: int) -> int:
		if self._shortened is None:
			return shown_position
		return self._shortened.original_index(shown_position)
	def _hidden_at(self, shown_position: int):
		if self._shortened is None:
			return None
		return self._shortened.hidden_at(shown_position)
	def _hidden_segments(self, hidden_range):
		start, stop = hidden_range
		return [
			segment for segment in self._segments
			if start < segment.end <= stop
		]
	def _show_hidden_menu(self, segments, pos):
		menu = QMenu(self)
		actions = {}
		for segment in segments:
			end = segment.end
			start = max(
				self._full_text.rfind('/', 0, end),
				self._full_text.rfind('\\', 0, end),
			) + 1
			actions[menu.addAction(self._full_text[start:end])] = segment
		menu_pos = QPoint(pos.x(), self.height())
		selected = menu.exec_(self.mapToGlobal(menu_pos))
		segment = actions.get(selected)
		if segment is not None:
			self.segment_clicked.emit(segment.url)
	def _shown_hidden_position(self, hidden_range):
		start, _stop = hidden_range
		removed = 0
		for current_start, current_stop in self._shortened.hidden:
			if current_start == start:
				return start - removed
			removed += current_stop - current_start - 1
		return None
	def leaveEvent(self, e):
		self._hovered_segment = None
		self._hovered_hidden_range = None
		self.unsetCursor()
		self.update()
		super().leaveEvent(e)
	def paintEvent(self, e):
		super().paintEvent(e)
		if self._hovered_segment is None and self._hovered_hidden_range is None:
			return
		contents = self.contentsRect()
		visible_start = self.cursorPositionAt(
			QPoint(contents.left() + 1, contents.center().y())
		)
		start = max(visible_start, 0)
		if self._hovered_hidden_range is not None:
			shown_position = self._shown_hidden_position(
				self._hovered_hidden_range
			)
			if shown_position is None or shown_position < start:
				return
			left = contents.left() + self.fontMetrics().horizontalAdvance(
				self.text()[start:shown_position]
			)
			width = self.fontMetrics().horizontalAdvance(
				self.text()[shown_position:shown_position + 1]
			)
		else:
			end = self._hovered_segment.end
			if self._shortened is not None:
				mapped_end = self._shortened.shown_index(end)
				if mapped_end is None:
					return
				end = mapped_end
			if start >= end:
				return
			left = contents.left()
			width = self.fontMetrics().horizontalAdvance(self.text()[start:end])
		if width <= 0:
			return
		color = QColor(self.palette().color(QPalette.Highlight))
		color.setAlpha(70)
		painter = QPainter(self)
		painter.fillRect(left, contents.top(), width, contents.height(), color)
