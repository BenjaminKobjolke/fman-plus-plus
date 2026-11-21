"""Drive and inspect the fman window through Qt's event loop."""

from dataclasses import asdict, dataclass, is_dataclass

from PyQt5.QtCore import QBuffer, QIODevice, QPoint, QPointF, Qt, QEvent
from PyQt5.QtGui import QContextMenuEvent, QHelpEvent, QMouseEvent, QTextDocument
from PyQt5.QtWidgets import (
	QAbstractItemView, QApplication, QDialogButtonBox, QHeaderView,
	QMenu, QMessageBox, QProgressDialog, QPushButton, QToolTip,
)

from fman.impl.overlay import Overlay
from fman.impl.quicksearch import Quicksearch
from fman.impl.prompt_popup import Prompt
from fman.impl.scripting.actions import get_pane
from fman.impl.scripting.native_readout import NativeReadout
from fman.impl.scripting.dialog_details import (
	prompt_font_sizes, quicksearch_details, rename_editor_details,
)
from fman.impl.scripting.external_drop import drop_files as send_drop
from fman.impl.scripting.window_capture import grab_with_progress_dialogs
from fman.impl.util.qt.key_events import post_chord, post_text
from fman.impl.util.qt.thread import run_in_main_thread


class UnknownFile(Exception):
	"""Raised when a requested URL is not displayed in a pane."""


class FileListHidden(Exception):
	"""Raised when a mounted view (folder tree or viewer) covers the pane's
	file list."""


class UnsafeDrag(Exception):
	"""Raised when a drag could start a file operation."""


class UnknownScreen(Exception):
	"""Raised when a requested screen index does not exist."""

	def __init__(self, screen_count):
		self.screen_count = screen_count
		super().__init__(screen_count)


@dataclass(frozen=True)
class WindowSize:
	width: int
	height: int
	available_width: int
	available_height: int
	screen_index: int | None = None


class AutomationActions:
	def __init__(self, main_window, plugin_support, native_readout=None):
		self._main_window = main_window
		self._plugin_support = plugin_support
		self._native_readout = native_readout or NativeReadout(
			main_window, plugin_support)

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
		if pane.get_mounted_widget() is not None:
			raise FileListHidden(file_url)
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
	def drop_files(self, request):
		pane = get_pane(self._plugin_support, self._main_window, request.pane)
		if pane.get_mounted_widget() is not None:
			raise FileListHidden('The file list is hidden behind a mounted view.')
		return send_drop(pane._widget.get_file_view(), request)

	@run_in_main_thread
	def drag_files(self, request):
		from fman.impl.scripting.pane_drag import drag_between

		source = get_pane(
			self._plugin_support, self._main_window, request.source_pane)
		target = get_pane(
			self._plugin_support, self._main_window, request.pane)
		if (source.get_mounted_widget() is not None
				or target.get_mounted_widget() is not None):
			raise FileListHidden(
				'The file list is hidden behind a mounted view.')
		return drag_between(source._widget.get_file_view(),
			target._widget.get_file_view(), request)

	@run_in_main_thread
	def click_at(self, x, y, button='left', double=False):
		target = self._window_target()
		point = QPoint(x, y)
		child = target.childAt(point) or target
		self._post_click(child, child.mapFrom(target, point), button, double)

	@run_in_main_thread
	def hover_at(self, x: int, y: int) -> dict[str, str | None]:
		target = self._window_target()
		point = QPoint(x, y)
		child = target.childAt(point) or target
		point = child.mapFrom(target, point)
		QToolTip.hideText()
		mouse_tracking = child.hasMouseTracking()
		if not mouse_tracking:
			child.setMouseTracking(True)
		try:
			QApplication.sendEvent(child, QEvent(QEvent.Enter))
			QApplication.sendEvent(child, QMouseEvent(
				QEvent.MouseMove, point, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
			QApplication.sendEvent(child, QHelpEvent(
				QEvent.ToolTip, point, child.mapToGlobal(point)))
		finally:
			if not mouse_tracking:
				child.setMouseTracking(False)
		if isinstance(child, QMenu):
			child.setActiveAction(child.actionAt(point))
		if not QToolTip.isVisible() and child.toolTip():
			QToolTip.showText(child.mapToGlobal(point), child.toolTip(), child)
		return {
			'widget': type(child).__name__,
			'tooltip': (
				QToolTip.text() if QToolTip.isVisible()
				else child.toolTip() or None
			),
		}

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
		target = self._window_target()
		pixmap = (
			grab_with_progress_dialogs(self._main_window)
			if target is self._main_window
			else target.grab()
		)
		pixmap.save(buffer, 'PNG')
		return bytes(buffer.data())

	@run_in_main_thread
	def screen_png(self):
		return self._native_readout.screen_png()

	@run_in_main_thread
	def native_windows(self):
		return self._native_readout.snapshot()

	@run_in_main_thread
	def close_native_windows(self):
		return self._native_readout.close_all()

	@run_in_main_thread
	def resize_window(self, width: int, height: int, x: int | None = None,
			y: int | None = None, screen: int | None = None) -> WindowSize:
		screens = QApplication.screens()
		if screen is not None:
			if screen < 0 or screen >= len(screens):
				raise UnknownScreen(len(screens))
			target_screen = screens[screen]
			available = target_screen.availableGeometry()
		self._main_window.showNormal()
		self._main_window.resize(width, height)
		if screen is not None:
			self._main_window.move(
				available.x() + (available.width() - width) // 2,
				available.y() + (available.height() - height) // 2,
			)
		elif x is not None or y is not None:
			current = self._main_window.frameGeometry().topLeft()
			self._main_window.move(current.x() if x is None else x,
				current.y() if y is None else y)
			target_screen = self._main_window.screen() or QApplication.primaryScreen()
			available = target_screen.availableGeometry()
		else:
			self._main_window.center_on_screen()
			target_screen = self._main_window.screen() or QApplication.primaryScreen()
			available = target_screen.availableGeometry()
		size = self._main_window.size()
		return WindowSize(
			size.width(), size.height(),
			available.width(), available.height(),
			screens.index(target_screen) if target_screen in screens else None,
		)

	@run_in_main_thread
	def get_dialog(self):
		dialog = QApplication.activeModalWidget() or \
			self._main_window.get_open_dialog()
		if dialog is None:
			dialog = next((widget for widget in QApplication.topLevelWidgets()
				if isinstance(widget, QProgressDialog) and widget.isVisible()), None)
		if dialog is None:
			dialog = next((widget for widget in
				self._main_window.findChildren(Overlay) if widget.isVisible()), None)
			if dialog is not None:
				document = QTextDocument()
				document.setHtml(dialog.label.text())
				return {
					'type': 'Overlay',
					'title': '',
					'text': document.toPlainText(),
					'buttons': [button.text().replace('&', '') for button in
						dialog.findChildren(QPushButton)],
				}
		if dialog is None:
			return rename_editor_details(self._main_window)
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
		if isinstance(dialog, Prompt):
			return {
				'type': type(dialog).__name__,
				'title': dialog.windowTitle(),
				'text': dialog.labelText(),
				'value': None if dialog.is_password() else dialog.textValue(),
				'buttons': [button.text() for button in dialog.findChild(
					QDialogButtonBox, 'buttons'
				).buttons()],
				'font_sizes': prompt_font_sizes(dialog),
			}
		if isinstance(dialog, Quicksearch):
			return quicksearch_details(dialog)
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
