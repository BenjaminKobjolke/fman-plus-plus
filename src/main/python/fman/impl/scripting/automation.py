"""Drive and inspect the fman window through Qt's event loop."""

from dataclasses import asdict, is_dataclass

from PyQt5.QtCore import QBuffer, QIODevice, QPoint, QPointF, Qt, QEvent
from PyQt5.QtGui import QContextMenuEvent, QMouseEvent
from PyQt5.QtWidgets import (
	QAbstractItemView, QApplication, QHeaderView, QMessageBox, QProgressDialog,
)

from fman.impl.scripting.actions import get_pane
from fman.impl.util.qt.key_events import post_chord, post_text
from fman.impl.util.qt.thread import run_in_main_thread


class UnknownFile(Exception):
	"""Raised when a requested URL is not displayed in a pane."""


class UnsafeDrag(Exception):
	"""Raised when a drag could start a file operation."""


class AutomationActions:
	def __init__(self, main_window, plugin_support):
		self._main_window = main_window
		self._plugin_support = plugin_support

	@run_in_main_thread
	def send_keys(self, chords):
		for chord in chords:
			post_chord(self._target(), chord)

	@run_in_main_thread
	def type_text(self, text):
		post_text(self._target(), text)

	@run_in_main_thread
	def get_visible_files(self, pane_index):
		pane = get_pane(self._plugin_support, self._main_window, pane_index)
		model = pane._widget.get_file_view().model()
		return [model.url(model.index(row, 0)) for row in range(model.rowCount())]

	@run_in_main_thread
	def get_viewer(self, pane_index: int) -> dict[str, object] | None:
		pane = get_pane(self._plugin_support, self._main_window, pane_index)
		widget = pane.get_mounted_widget()
		if widget is None:
			return None
		result = {'type': type(widget).__name__}
		playback_state = getattr(widget, 'playback_state', None)
		if callable(playback_state):
			state = playback_state()
			result['playback'] = (
				asdict(state) if is_dataclass(state) else vars(state)
			)
		return result

	@run_in_main_thread
	def click_file(self, pane_index, file_url, button='left', double=False):
		pane = get_pane(self._plugin_support, self._main_window, pane_index)
		view = pane._widget.get_file_view()
		model = view.model()
		try:
			index = model.find(file_url)
		except (ValueError, KeyError):
			raise UnknownFile(file_url) from None
		if not index.isValid():
			raise UnknownFile(file_url)
		view.scrollTo(index)
		point = view.visualRect(index).center()
		self._post_click(view.viewport(), point, button, double)

	@run_in_main_thread
	def click_at(self, x, y, button='left', double=False):
		target = self._window_target()
		point = QPoint(x, y)
		child = target.childAt(point) or target
		self._post_click(child, child.mapFrom(target, point), button, double)

	@run_in_main_thread
	def drag_at(self, start: QPoint, end: QPoint) -> None:
		target = self._window_target()
		child = target.childAt(start) or target
		parent = child.parent()
		if (
			isinstance(parent, QAbstractItemView)
			and not isinstance(parent, QHeaderView)
			and child is parent.viewport()
		):
			raise UnsafeDrag('Drags may not start on a file list.')

		start = child.mapFrom(target, start)
		end = child.mapFrom(target, end)
		QApplication.postEvent(child, QMouseEvent(
			QEvent.MouseButtonPress, QPointF(start), Qt.LeftButton,
			Qt.LeftButton, Qt.NoModifier))
		for step in range(1, 6):
			point = QPointF(
				start.x() + (end.x() - start.x()) * step / 5,
				start.y() + (end.y() - start.y()) * step / 5,
			)
			QApplication.postEvent(child, QMouseEvent(
				QEvent.MouseMove, point, Qt.NoButton,
				Qt.LeftButton, Qt.NoModifier))
		QApplication.postEvent(child, QMouseEvent(
			QEvent.MouseButtonRelease, QPointF(end), Qt.LeftButton,
			Qt.NoButton, Qt.NoModifier))

	@run_in_main_thread
	def screenshot_png(self):
		buffer = QBuffer()
		buffer.open(QIODevice.WriteOnly)
		self._window_target().grab().save(buffer, 'PNG')
		return bytes(buffer.data())

	@run_in_main_thread
	def get_dialog(self):
		dialog = QApplication.activeModalWidget() or \
			self._main_window.get_open_dialog()
		if dialog is None:
			dialog = next((widget for widget in QApplication.topLevelWidgets()
				if isinstance(widget, QProgressDialog) and widget.isVisible()), None)
		if dialog is None:
			return None
		if isinstance(dialog, QProgressDialog):
			return {
				'type': type(dialog).__name__,
				'title': dialog.windowTitle(),
				'text': dialog.labelText(),
				'buttons': [],
				'progress': {
					'value': dialog.value(),
					'maximum': dialog.maximum(),
				},
			}
		if not isinstance(dialog, QMessageBox):
			return {
				'type': type(dialog).__name__,
				'title': dialog.windowTitle(),
				'text': '',
				'buttons': [],
			}
		return {
			'type': type(dialog).__name__,
			'title': dialog.windowTitle(),
			'text': dialog.text(),
			'buttons': [button.text() for button in dialog.buttons()],
		}

	def _window_target(self):
		return QApplication.activeModalWidget() \
			or QApplication.activePopupWidget() or self._main_window

	def _target(self):
		window = self._window_target()
		return window.focusWidget() or window

	@staticmethod
	def _post_click(target, point, button, double):
		global_point = target.mapToGlobal(point)
		if button == 'right':
			QApplication.postEvent(target, QContextMenuEvent(
				QContextMenuEvent.Mouse, point, global_point))
			return
		QApplication.postEvent(target, QMouseEvent(
			QEvent.MouseButtonPress, QPointF(point), Qt.LeftButton,
			Qt.LeftButton, Qt.NoModifier))
		QApplication.postEvent(target, QMouseEvent(
			QEvent.MouseButtonRelease, QPointF(point), Qt.LeftButton,
			Qt.NoButton, Qt.NoModifier))
		if double:
			QApplication.postEvent(target, QMouseEvent(
				QEvent.MouseButtonDblClick, QPointF(point), Qt.LeftButton,
				Qt.LeftButton, Qt.NoModifier))
			QApplication.postEvent(target, QMouseEvent(
				QEvent.MouseButtonRelease, QPointF(point), Qt.LeftButton,
				Qt.NoButton, Qt.NoModifier))
