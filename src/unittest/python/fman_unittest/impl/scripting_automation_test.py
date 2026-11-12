"""Qt event tests for the scripting API's desktop automation actions."""

from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace

from PyQt5.QtCore import QEvent, QPoint
from PyQt5.QtGui import QImage, QStandardItemModel
from PyQt5.QtWidgets import (
	QApplication, QDialog, QHeaderView, QMessageBox, QProgressDialog,
	QTableView, QWidget,
)

from fman.impl.scripting.automation import (
	AutomationActions, UnknownFile, UnsafeDrag,
)
from fman.impl.scripting.actions import InvalidPane
from fman.impl.util.qt.key_events import parse_chord, post_chord, post_text
from fman.impl.widgets import MessageBox


class ScriptingAutomationTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def test_chords_and_text_are_posted_to_the_target(self):
		widget = _KeyCapture()
		widget.show()
		self.addCleanup(widget.close)
		post_chord(widget, 'Ctrl+P')
		post_text(widget, 'x')
		self.app.processEvents()
		self.assertEqual(
			[(QEvent.KeyPress, ''), (QEvent.KeyRelease, ''),
			 (QEvent.KeyPress, 'x'), (QEvent.KeyRelease, 'x')], widget.events)

	def test_chord_parser_rejects_multiple_chords(self):
		with self.assertRaises(ValueError):
			parse_chord('Ctrl+A, Ctrl+B')

	def test_screenshot_returns_a_decodable_png_of_the_window(self):
		window = QWidget()
		window.setFixedSize(40, 30)
		window.show()
		self.addCleanup(window.close)
		data = AutomationActions(window, None).screenshot_png()
		self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
		image = QImage.fromData(data, 'PNG')
		self.assertFalse(image.isNull())
		self.assertEqual(window.grab().size(), image.size())

	def test_get_dialog_returns_none_without_an_active_modal_widget(self):
		actions = AutomationActions(_Window(), None)
		with patch('fman.impl.scripting.automation.QApplication.activeModalWidget',
				return_value=None):
			self.assertIsNone(actions.get_dialog())

	def test_get_dialog_returns_open_embedded_dialog(self):
		dialog = QDialog()
		dialog.setWindowTitle('Quicksearch')
		actions = AutomationActions(_WindowWithDialog(dialog), None)
		with patch('fman.impl.scripting.automation.QApplication.activeModalWidget',
				return_value=None):
			self.assertEqual({
				'type': 'QDialog',
				'title': 'Quicksearch',
				'text': '',
				'buttons': [],
			}, actions.get_dialog())

	def test_get_dialog_returns_message_box_details(self):
		parent = QWidget()
		dialog = MessageBox(parent)
		dialog.setWindowTitle('Confirm deletion')
		dialog.setText('Move this file to the Recycle Bin?')
		dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
		actions = AutomationActions(_Window(), None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=dialog,
		):
			self.assertEqual({
				'type': 'MessageBox',
				'title': 'Confirm deletion',
				'text': 'Move this file to the Recycle Bin?',
				'buttons': ['&Yes', '&No'],
			}, actions.get_dialog())

	def test_get_dialog_returns_visible_progress_dialog_details(self):
		dialog = QProgressDialog('Downloading component...', '', 0, 100)
		dialog.setWindowTitle('Downloading video player component (one-time)...')
		dialog.setValue(40)
		dialog.show()
		self.addCleanup(dialog.close)
		actions = AutomationActions(_Window(), None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		), patch.object(_Window, 'get_open_dialog', return_value=None):
			self.assertEqual({
				'type': 'QProgressDialog',
				'title': 'Downloading video player component (one-time)...',
				'text': 'Downloading component...',
				'buttons': [],
				'progress': {'value': 40, 'maximum': 100},
			}, actions.get_dialog())

	def test_get_dialog_ignores_hidden_progress_dialog(self):
		dialog = QProgressDialog('Downloading component...', '', 0, 100)
		dialog.hide()
		self.addCleanup(dialog.close)
		actions = AutomationActions(_Window(), None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		), patch.object(_Window, 'get_open_dialog', return_value=None):
			self.assertIsNone(actions.get_dialog())

	def test_visible_files_follow_the_model_display_order(self):
		model = _Rows(['file:///second', 'file:///first'])
		pane = _Pane(model)
		plugin_support = _PluginSupport(pane)
		actions = AutomationActions(_Window(), plugin_support)
		self.assertEqual(
			['file:///second', 'file:///first'], actions.get_visible_files(0))

	def test_get_viewer_returns_none_when_no_widget_is_mounted(self):
		pane = _Pane(_Rows([]))
		pane.get_mounted_widget = lambda: None
		actions = AutomationActions(_Window(), _PluginSupport(pane))
		self.assertIsNone(actions.get_viewer(0))

	def test_get_viewer_includes_optional_playback_state(self):
		pane = _Pane(_Rows([]))
		pane.get_mounted_widget = lambda: _MountedWidget(
			SimpleNamespace(
				loaded=True, paused=False, position=12.5, duration=30.0,
			))
		actions = AutomationActions(_Window(), _PluginSupport(pane))
		self.assertEqual({
			'type': '_MountedWidget',
			'playback': {
				'loaded': True, 'paused': False,
				'position': 12.5, 'duration': 30.0,
			},
		}, actions.get_viewer(0))

	def test_get_viewer_omits_playback_state_when_widget_has_no_method(self):
		pane = _Pane(_Rows([]))
		pane.get_mounted_widget = lambda: QWidget()
		actions = AutomationActions(_Window(), _PluginSupport(pane))
		self.assertEqual({'type': 'QWidget'}, actions.get_viewer(0))

	def test_click_at_posts_press_release_and_double_click_events(self):
		window = _MouseCapture()
		window.resize(40, 30)
		window.show()
		self.addCleanup(window.close)
		actions = AutomationActions(window, None)
		actions.click_at(5, 6, 'left', True)
		self.app.processEvents()
		self.assertEqual([
			QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
			QEvent.MouseButtonDblClick, QEvent.MouseButtonRelease,
		], window.events)

	def test_drag_at_posts_press_moves_and_release(self):
		window = _MouseCapture()
		window.resize(40, 30)
		window.show()
		self.addCleanup(window.close)
		AutomationActions(window, None).drag_at(QPoint(5, 6), QPoint(25, 16))
		self.app.processEvents()
		self.assertEqual(QEvent.MouseButtonPress, window.events[0])
		self.assertGreaterEqual(window.events.count(QEvent.MouseMove), 1)
		self.assertTrue(all(
			event == QEvent.MouseMove for event in window.events[1:-1]))
		self.assertEqual(QEvent.MouseButtonRelease, window.events[-1])

	def test_drag_at_rejects_file_list_viewport(self):
		view = _table_view()
		view.show()
		self.addCleanup(view.close)
		point = view.viewport().rect().center()
		with self.assertRaises(UnsafeDrag):
			AutomationActions(view, None).drag_at(point, point + QPoint(10, 0))

	def test_drag_at_allows_column_header(self):
		view = _table_view()
		view.show()
		self.addCleanup(view.close)
		header = view.horizontalHeader()
		self.assertIsInstance(header, QHeaderView)
		header.resizeSection(0, 120)
		header_point = QPoint(
			header.sectionViewportPosition(0) + header.sectionSize(0) - 1,
			header.height() // 2,
		)
		start = header.mapTo(view, header_point)
		end = start + QPoint(-20, 0)
		initial_width = header.sectionSize(0)
		AutomationActions(view, None).drag_at(
			start, end)
		self.app.processEvents()
		self.assertLess(header.sectionSize(0), initial_width)

	def test_right_click_posts_context_menu_event(self):
		window = _MouseCapture()
		window.resize(40, 30)
		window.show()
		self.addCleanup(window.close)
		AutomationActions(window, None).click_at(5, 6, 'right')
		self.app.processEvents()
		self.assertEqual([QEvent.ContextMenu], window.events)

	def test_invalid_pane_index_uses_shared_validation(self):
		pane = _Pane(_Rows([]))
		actions = AutomationActions(_Window(), _PluginSupport(pane))
		with self.assertRaises(InvalidPane):
			actions.get_visible_files(2)

	def test_click_file_rejects_invalid_model_index(self):
		model = _FindModel(_InvalidIndex())
		pane = _Pane(model)
		actions = AutomationActions(_Window(), _PluginSupport(pane))
		with self.assertRaises(UnknownFile):
			actions.click_file(0, 'file:///hidden')
		self.assertFalse(pane._widget.get_file_view().scrolled)


class _KeyCapture(QWidget):
	def __init__(self):
		super().__init__()
		self.events = []

	def event(self, event):
		if event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
			self.events.append((event.type(), event.text()))
			return True
		return super().event(event)


class _Rows:
	def __init__(self, urls):
		self.urls = urls

	def rowCount(self):
		return len(self.urls)

	def index(self, row, _column):
		return row

	def url(self, index):
		return self.urls[index]


class _View:
	def __init__(self, model):
		self._model = model
		self.scrolled = False

	def model(self):
		return self._model

	def scrollTo(self, _index):
		self.scrolled = True


class _FindModel:
	def __init__(self, index):
		self.index = index

	def find(self, _url):
		return self.index


class _InvalidIndex:
	@staticmethod
	def isValid():
		return False


class _Widget:
	def __init__(self, model):
		self._view = _View(model)

	def get_file_view(self):
		return self._view


class _MountedWidget:
	def __init__(self, state):
		self._state = state

	def playback_state(self):
		return self._state


class _Pane:
	def __init__(self, model):
		self._widget = _Widget(model)


class _PluginSupport:
	def __init__(self, pane):
		self.pane = pane

	def get_panes(self):
		return [self.pane]

	def get_active_pane(self):
		return self.pane


class _Window:
	@staticmethod
	def focusWidget():
		return None
	@staticmethod
	def get_open_dialog():
		return None


class _WindowWithDialog(_Window):
	def __init__(self, dialog):
		self._dialog = dialog
	def get_open_dialog(self):
		return self._dialog


class _MouseCapture(QWidget):
	def __init__(self):
		super().__init__()
		self.events = []

	def event(self, event):
		if event.type() in (
			QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
			QEvent.MouseButtonDblClick, QEvent.MouseMove, QEvent.ContextMenu,
		):
			self.events.append(event.type())
			return True
		return super().event(event)


def _table_view():
	view = QTableView()
	model = QStandardItemModel(2, 2, view)
	view.setModel(model)
	return view
