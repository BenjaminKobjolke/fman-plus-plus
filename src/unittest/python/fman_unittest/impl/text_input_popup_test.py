"""Tests for the multiline text input dialog."""

from fman.impl.text_input_popup import TextInputPrompt
from fman.impl.frameless_dialog import text_width_floor
from fman.impl.widgets import MainWindow
from fman.localization import translate
from fman.localization_keys import (
	PROMPT_CANCEL, PROMPT_OK, QUICKSEARCH_KEY_ENTER,
	QUICKSEARCH_KEY_SHIFT_ENTER, TEXT_INPUT_NEW_LINE, TEXT_INPUT_SAVE,
)
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import (
	QApplication, QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QWidget,
)
from unittest import TestCase


class TextInputPromptTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.parent = QWidget()
		self.dialog = TextInputPrompt(
			self.parent, 'Comment for file.txt', 'prefilled'
		)
		self.addCleanup(self.dialog.close)

	def test_prefills_and_selects_text(self):
		editor = self.dialog.findChild(QPlainTextEdit, 'text')
		self.assertEqual('prefilled', editor.toPlainText())
		self.assertEqual('prefilled', editor.textCursor().selectedText())

	def test_enter_accepts_and_returns_plain_text(self):
		self.dialog.show()
		QTest.keyClick(self.dialog.findChild(QPlainTextEdit, 'text'), Qt.Key_Return)
		self.assertEqual(QDialog.Accepted, self.dialog.result())
		self.assertEqual('prefilled', self.dialog.textValue())

	def test_shift_enter_inserts_newline_without_accepting(self):
		self.dialog.show()
		editor = self.dialog.findChild(QPlainTextEdit, 'text')
		editor.moveCursor(editor.textCursor().End)
		QTest.keyClick(editor, Qt.Key_Return, Qt.ShiftModifier)
		self.assertEqual('prefilled\n', editor.toPlainText())
		self.assertEqual(0, self.dialog.result())

	def test_escape_rejects(self):
		self.dialog.show()
		QTest.keyClick(self.dialog.findChild(QPlainTextEdit, 'text'), Qt.Key_Escape)
		self.assertEqual(QDialog.Rejected, self.dialog.result())

	def test_footer_explains_enter_and_shift_enter(self):
		footer = self.dialog.findChild(QLabel, 'footer')
		self.assertEqual(
			'%s  %s    %s  %s' % (
				translate(QUICKSEARCH_KEY_ENTER), translate(TEXT_INPUT_SAVE),
				translate(QUICKSEARCH_KEY_SHIFT_ENTER),
				translate(TEXT_INPUT_NEW_LINE),
			), footer.text()
		)

	def test_buttons_are_translated_and_have_no_keyboard_focus(self):
		buttons = self.dialog.findChild(QDialogButtonBox, 'buttons')
		self.assertEqual(
			translate(PROMPT_OK), buttons.button(QDialogButtonBox.Ok).text()
		)
		self.assertEqual(
			translate(PROMPT_CANCEL), buttons.button(QDialogButtonBox.Cancel).text()
		)
		for button in buttons.buttons():
			self.assertEqual(Qt.NoFocus, button.focusPolicy())
			self.assertFalse(button.autoDefault())
			self.assertFalse(button.isDefault())

	def test_uses_frameless_prompt_margins_and_minimum_text_width(self):
		self.assertTrue(self.dialog.property('frameless'))
		self.assertEqual(
			text_width_floor(self.dialog),
			self.dialog.findChild(QPlainTextEdit, 'text').minimumWidth()
		)

	def test_main_window_api_returns_text_on_accept_and_none_on_cancel(self):
		class StubWindow(QWidget):
			_app = _StubApp()
			def exec_dialog(self, dialog):
				self.dialog = dialog
				return self.accept

		window = StubWindow()
		window.accept = True
		self.assertEqual(
			'initial', MainWindow.show_text_input(window, 'Title', 'initial')
		)
		self.assertIsInstance(window.dialog, TextInputPrompt)
		window.accept = False
		self.assertIsNone(MainWindow.show_text_input(window, 'Title', 'initial'))


class _StubApp:
	def exit(self, _code):
		pass
