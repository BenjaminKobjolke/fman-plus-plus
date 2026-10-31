"""Qt event tests for the scripting API's desktop automation actions."""

from unittest import TestCase
from unittest.mock import patch

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QWidget

from fman.impl.scripting.automation import AutomationActions, UnknownFile
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

	def test_screenshot_returns_png_bytes(self):
		window = QWidget()
		window.resize(40, 30)
		window.show()
		self.addCleanup(window.close)
		data = AutomationActions(window, None).screenshot_png()
		self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))

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

	def test_visible_files_follow_the_model_display_order(self):
		model = _Rows(['file:///second', 'file:///first'])
		pane = _Pane(model)
		plugin_support = _PluginSupport(pane)
		actions = AutomationActions(_Window(), plugin_support)
		self.assertEqual(
			['file:///second', 'file:///first'], actions.get_visible_files(0))

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
			QEvent.MouseButtonDblClick, QEvent.ContextMenu,
		):
			self.events.append(event.type())
			return True
		return super().event(event)
