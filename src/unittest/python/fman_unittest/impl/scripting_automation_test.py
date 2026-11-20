"""Qt event tests for the scripting API's desktop automation actions."""

from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace

from PyQt5.QtCore import QEvent, QPoint
from PyQt5.QtGui import QColor, QImage, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
	QApplication, QDialog, QDialogButtonBox, QHeaderView, QLabel, QLineEdit,
	QMenu, QMessageBox, QProgressDialog,
	QTableView, QWidget,
)

from fman.impl.overlay import Overlay
from fman.impl.quicksearch import Quicksearch
from fman.impl.prompt_popup import Prompt
from fman.impl.scripting.automation import (
	AutomationActions, FileListHidden, UnknownFile, UnknownScreen, UnsafeDrag,
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

	def test_screenshot_paints_visible_progress_dialog_over_window(self):
		window, dialog = self._progress_dialog_window()
		dialog.show()
		dialog.move(20, 20)
		self.app.processEvents()

		image = QImage.fromData(
			AutomationActions(window, None).screenshot_png(), 'PNG')

		self.assertEqual(window.grab().size(), image.size())
		dialog_point = window.mapFromGlobal(
			dialog.mapToGlobal(QPoint(10, 10)))
		self.assertNotEqual(
			QColor('red'), image.pixelColor(dialog_point))
		self.assertEqual(QColor('red'), image.pixelColor(295, 195))

	def test_screenshot_does_not_paint_hidden_progress_dialog(self):
		window, dialog = self._progress_dialog_window()
		dialog.show()
		dialog.move(20, 20)
		dialog.hide()
		self.app.processEvents()

		image = QImage.fromData(
			AutomationActions(window, None).screenshot_png(), 'PNG')

		self.assertEqual(QColor('red'), image.pixelColor(30, 30))

	def _progress_dialog_window(self):
		window = QWidget()
		window.setFixedSize(300, 200)
		window.setAutoFillBackground(True)
		palette = window.palette()
		palette.setColor(window.backgroundRole(), QColor('red'))
		window.setPalette(palette)
		window.show()
		self.addCleanup(window.close)

		dialog = QProgressDialog(window)
		dialog.setAutoFillBackground(True)
		palette = dialog.palette()
		palette.setColor(dialog.backgroundRole(), QColor('blue'))
		dialog.setPalette(palette)
		dialog.setMinimumDuration(0)
		self.addCleanup(dialog.close)
		return window, dialog

	def test_resize_window_resizes_and_reports_available_area(self):
		window = _ResizableWindow()
		window.resize(320, 240)
		window.show()
		self.addCleanup(window.close)
		result = AutomationActions(window, None).resize_window(640, 480)
		self.assertEqual((640, 480), (window.width(), window.height()))
		self.assertEqual((640, 480), (result.width, result.height))
		self.assertGreater(result.available_width, 0)
		self.assertGreater(result.available_height, 0)

	def test_resize_window_resizes_to_requested_size(self):
		window = _ResizableWindow()
		window.show()
		self.addCleanup(window.close)
		AutomationActions(window, None).resize_window(300, 200)
		self.assertEqual((300, 200), (window.width(), window.height()))

	def test_resize_window_moves_to_global_position(self):
		window = _ResizableWindow()
		window.show()
		self.addCleanup(window.close)
		AutomationActions(window, None).resize_window(300, 200, x=25, y=35)
		self.assertEqual(
			(25, 35), (window.frameGeometry().x(), window.frameGeometry().y()),
		)

	def test_resize_window_rejects_unknown_screen_with_screen_count(self):
		window = _ResizableWindow()
		window.resize(320, 240)
		with self.assertRaises(UnknownScreen) as caught:
			AutomationActions(window, None).resize_window(
				300, 200, screen=len(QApplication.screens()))
		self.assertEqual(
			len(QApplication.screens()), caught.exception.screen_count,
		)
		self.assertEqual((320, 240), (window.width(), window.height()))

	def test_resize_window_centers_on_selected_screen(self):
		window = _ResizableWindow()
		window.show()
		self.addCleanup(window.close)
		result = AutomationActions(window, None).resize_window(300, 200, screen=0)
		available = QApplication.screens()[0].availableGeometry()
		self.assertEqual(0, result.screen_index)
		self.assertEqual(
			(available.x() + (available.width() - 300) // 2,
			 available.y() + (available.height() - 200) // 2),
			(window.frameGeometry().x(), window.frameGeometry().y()),
		)

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

	def test_get_dialog_reports_quicksearch_text_and_font_sizes(self):
		parent = QWidget()
		parent.resize(900, 700)
		self.addCleanup(parent.close)
		previous_style_sheet = self.app.styleSheet()
		self.addCleanup(self.app.setStyleSheet, previous_style_sheet)
		self.app.setStyleSheet(
			'* { font-size: 20pt; } Quicksearch QLineEdit { font-size: 16pt; }')
		dialog = Quicksearch(
			parent, _StubApp(), {}, lambda _query: [], query='search text',
			title='Command Palette', alt_accept=True)
		self.addCleanup(dialog.close)
		dialog.show()
		self.app.processEvents()
		footer = dialog.findChild(QLabel, 'footer')
		actions = AutomationActions(_WindowWithDialog(dialog), None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		):
			result = actions.get_dialog()
		self.assertEqual('Quicksearch', result['type'])
		self.assertEqual('Command Palette', result['title'])
		self.assertEqual('search text', result['value'])
		self.assertEqual(footer.text(), result['text'])
		self.assertEqual(
			{'title': 18.0, 'value': 16.0, 'footer': 14.0},
			result['font_sizes'])

	def test_get_dialog_reports_no_font_size_for_hidden_quicksearch_header(self):
		parent = QWidget()
		self.addCleanup(parent.close)
		dialog = Quicksearch(
			parent, _StubApp(), {}, lambda _query: [], query='search text',
			title='')
		self.addCleanup(dialog.close)
		dialog.show()
		self.app.processEvents()
		actions = AutomationActions(_WindowWithDialog(dialog), None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		):
			result = actions.get_dialog()
		self.assertIsNone(result['font_sizes']['title'])

	def test_get_dialog_returns_prompt_message_value_and_buttons(self):
		parent = QWidget()
		self.addCleanup(parent.close)
		prompt = _make_prompt(parent, 'Copy "folder" to\nC:/target', 'folder')
		self.addCleanup(prompt.close)
		buttons = prompt.findChild(QDialogButtonBox, 'buttons')
		header = prompt.findChild(QLabel, 'header')
		value = prompt.focusProxy()
		detail = prompt.findChild(QLabel, 'detail')
		for widget in (header, value, detail):
			widget.ensurePolished()
		actions = AutomationActions(_WindowWithDialog(prompt), None)
		with patch('fman.impl.scripting.automation.QApplication.activeModalWidget',
				return_value=None):
			self.assertEqual({
				'type': 'Prompt',
			'title': 'Quicksearch',
				'text': 'Copy "folder" to\nC:/target',
				'value': 'folder',
				'buttons': [button.text() for button in buttons.buttons()],
				'font_sizes': {
					'title': header.font().pointSizeF(),
					'value': value.font().pointSizeF(),
					'detail': detail.font().pointSizeF(),
				},
			}, actions.get_dialog())

	def test_get_dialog_reports_inline_rename_editor(self):
		window = QWidget()
		view = QTableView(window)
		model = QStandardItemModel(1, 1, view)
		model.setItem(0, 0, QStandardItem('original.txt'))
		view.setModel(model)
		window.show()
		view.show()
		self.addCleanup(window.close)
		index = model.index(0, 0)
		view.setCurrentIndex(index)
		view.edit(index)
		self.app.processEvents()
		editors = [editor for editor in view.viewport().findChildren(QLineEdit)
			if editor.isVisible()]
		self.assertTrue(editors)
		editors[0].setText('renamed')
		actions = AutomationActions(window, None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		), patch.object(
			window, 'get_open_dialog', return_value=None, create=True,
		):
			result = actions.get_dialog()
		self.assertEqual({
			'type': 'RenameEditor', 'title': '', 'text': 'original.txt',
			'value': 'renamed', 'buttons': [],
			'font_sizes': {'value': editors[0].font().pointSizeF()},
		}, result)

	def test_get_dialog_returns_none_without_inline_rename_editor(self):
		window = QWidget()
		view = QTableView(window)
		view.setModel(QStandardItemModel(1, 1, view))
		window.show()
		self.addCleanup(window.close)
		actions = AutomationActions(window, None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		), patch.object(
			window, 'get_open_dialog', return_value=None, create=True,
		):
			self.assertIsNone(actions.get_dialog())

	def test_get_dialog_does_not_expose_password_prompt_value(self):
		parent = QWidget()
		self.addCleanup(parent.close)
		prompt = _make_prompt(parent, 'Password', 'secret', password=True)
		self.addCleanup(prompt.close)
		actions = AutomationActions(_WindowWithDialog(prompt), None)
		with patch('fman.impl.scripting.automation.QApplication.activeModalWidget',
				return_value=None):
			result = actions.get_dialog()
		self.assertIsNone(result['value'])
		self.assertIsNone(result['font_sizes']['detail'])
		self.assertNotIn('secret', str(result))

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

	def test_get_dialog_reports_visible_tutorial_overlay(self):
		window = QWidget()
		window.resize(400, 300)
		window.show()
		self.addCleanup(window.close)
		overlay = Overlay(window, '<b>Welcome</b><br>Take a tour', [
			('&No thanks', lambda: None), ('&Yes', lambda: None),
		])
		overlay.show()
		self.addCleanup(overlay.close)
		self.app.processEvents()
		actions = AutomationActions(window, None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		), patch.object(window, 'get_open_dialog', return_value=None, create=True):
			self.assertEqual({
				'type': 'Overlay', 'title': '', 'text': 'Welcome\nTake a tour',
				'buttons': ['No thanks', 'Yes'],
			}, actions.get_dialog())

	def test_get_dialog_ignores_hidden_tutorial_overlay(self):
		window = QWidget()
		self.addCleanup(window.close)
		overlay = Overlay(window, '<b>Welcome</b>', [('&No', lambda: None)])
		self.addCleanup(overlay.close)
		actions = AutomationActions(window, None)
		with patch(
			'fman.impl.scripting.automation.QApplication.activeModalWidget',
			return_value=None,
		), patch.object(window, 'get_open_dialog', return_value=None, create=True):
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

	def test_hover_at_reports_tooltip_and_sends_mouse_move(self):
		window = _MouseCapture()
		window.resize(40, 30)
		window.setMouseTracking(True)
		window.setToolTip('full path')
		window.show()
		self.addCleanup(window.close)

		result = AutomationActions(window, None).hover_at(5, 6)

		self.assertEqual('full path', result['tooltip'])
		self.assertEqual('_MouseCapture', result['widget'])
		self.assertIn(QEvent.MouseMove, window.events)

	def test_hover_at_returns_none_when_widget_has_no_tooltip(self):
		window = _MouseCapture()
		window.resize(40, 30)
		window.show()
		self.addCleanup(window.close)

		self.assertIsNone(
			AutomationActions(window, None).hover_at(5, 6)['tooltip'])

	def test_hover_at_highlights_a_menu_action(self):
		menu = QMenu()
		self.addCleanup(menu.close)
		action = menu.addAction('parent folder')
		menu.popup(QPoint(100, 100))
		self.app.processEvents()
		point = menu.actionGeometry(action).center()

		AutomationActions(menu, None).hover_at(point.x(), point.y())

		self.assertIs(action, menu.activeAction())

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

	def test_click_file_refuses_while_a_view_hides_the_file_list(self):
		pane = _Pane(_FindModel(_InvalidIndex()))
		pane.mounted = object()
		actions = AutomationActions(_Window(), _PluginSupport(pane))

		with self.assertRaises(FileListHidden):
			actions.click_file(0, 'file:///hidden')

		self.assertFalse(pane._widget.get_file_view().scrolled)


class _ResizableWindow(QWidget):
	def center_on_screen(self):
		pass


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
		self.mounted = None

	def get_mounted_widget(self):
		return self.mounted


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
	@staticmethod
	def findChildren(_widget_type):
		return []


class _WindowWithDialog(_Window):
	def __init__(self, dialog):
		self._dialog = dialog
	def get_open_dialog(self):
		return self._dialog


def _make_prompt(parent, message, default='', password=False):
	css = {
		'border-top-width_px': 0, 'border-bottom-width_px': 1,
		'padding-top_px': 5, 'padding-left_px': 7, 'padding-right_px': 7,
		'title': {'font-size_pts': 11, 'color': QColor('#fff'),
			'highlight': {'color': QColor('#f00')}},
		'hint': {'font-size_pts': 9, 'color': QColor('#aaa')},
		'description': {'font-size_pts': 9, 'color': QColor('#aaa')},
	}
	return Prompt(parent, _StubApp(), css, message, default, password=password)


class _StubApp:
	def exit(self, _code):
		pass


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
