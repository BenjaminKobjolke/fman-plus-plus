"""Focus, positioning and cancellation behavior of in-window dialogs."""

from unittest import TestCase

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QDialog, QLineEdit, QMessageBox, \
	QVBoxLayout, QWidget

from fman.impl.in_window_dialog import Scrim, exec_in_window
from fman.impl.prompt_popup import Prompt
from fman.impl.widgets import MessageBox


class InWindowDialogTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.parent = _Window()
		self.parent.resize(600, 400)
		self.edit = QLineEdit(self.parent)
		QVBoxLayout(self.parent).addWidget(self.edit)
		self.parent.show()
		self.app.processEvents()
		self.parent.activateWindow()
		self.edit.setFocus()
		self.app.processEvents()

	def tearDown(self):
		self.parent.close()
		self.app.processEvents()

	def test_dialog_runs_non_modally_as_child_and_returns_result(self):
		dialog = QDialog()
		observed = []
		def check_and_accept():
			observed.append((
				QApplication.activeModalWidget(), dialog.isWindow(),
				dialog.parentWidget() is self.parent
			))
			dialog.accept()
		QTimer.singleShot(0, check_and_accept)
		self.assertEqual(QDialog.Accepted, exec_in_window(dialog, self.parent))
		self.assertEqual([(None, False, True)], observed)

	def test_plain_dialog_gets_the_frameless_outline_style(self):
		dialog = QDialog()
		observed = []
		def check_and_accept():
			observed.append(dialog.property('frameless'))
			dialog.accept()
		QTimer.singleShot(0, check_and_accept)
		self.assertEqual(QDialog.Accepted, exec_in_window(dialog, self.parent))
		self.assertEqual([True], observed)

	def test_message_box_gets_the_frameless_outline_style(self):
		dialog = MessageBox(self.parent, True)
		dialog.setText('Are you sure?')
		dialog.setStandardButtons(QMessageBox.Ok)
		# A real QMessageBox window aborts under Qt's offscreen platform.
		dialog.show = lambda: None
		observed = []
		def check_and_accept():
			observed.append(dialog.property('frameless'))
			dialog.accept()
		QTimer.singleShot(0, check_and_accept)
		self.assertEqual(QDialog.Accepted, exec_in_window(dialog, self.parent))
		self.assertEqual([True], observed)

	def test_escape_rejects_dialog(self):
		dialog = _DialogWithLineEdit()
		QTimer.singleShot(0, lambda: QTest.keyClick(dialog.edit, Qt.Key_Escape))
		self.assertEqual(QDialog.Rejected, exec_in_window(dialog, self.parent))

	def test_scrim_click_rejects_and_scrim_is_removed(self):
		dialog = QDialog()
		def click_scrim():
			QTest.mouseClick(self.parent.findChild(Scrim), Qt.LeftButton)
		QTimer.singleShot(0, click_scrim)
		self.assertEqual(QDialog.Rejected, exec_in_window(dialog, self.parent))
		self.assertIsNone(self.parent.findChild(Scrim))

	def test_parent_resize_updates_scrim_and_dialog_position(self):
		dialog = QDialog()
		dialog.resize(200, 100)
		observed = []
		def resize_and_check():
			self.parent.resize(120, 80)
			self.app.processEvents()
			scrim = self.parent.findChild(Scrim)
			observed.append((scrim.geometry(), dialog.pos()))
			dialog.reject()
		QTimer.singleShot(0, resize_and_check)
		self.assertEqual(QDialog.Rejected, exec_in_window(dialog, self.parent))
		self.assertEqual((self.parent.rect(), dialog.pos()), observed[0])
		self.assertEqual((0, 0), (dialog.x(), dialog.y()))

	def test_dialog_resize_recenters_it_in_parent(self):
		dialog = QDialog()
		dialog.resize(200, 100)
		observed = []
		def resize_and_check():
			dialog.resize(300, 180)
			self.app.processEvents()
			observed.append(dialog.pos())
			dialog.reject()
		QTimer.singleShot(0, resize_and_check)
		self.assertEqual(QDialog.Rejected, exec_in_window(dialog, self.parent))
		self.assertEqual(
			((self.parent.width() - dialog.width()) // 2,
			 (self.parent.height() - dialog.height()) // 2),
			(observed[0].x(), observed[0].y())
		)

	def test_focus_returns_to_widget_focused_before_call(self):
		dialog = QDialog()
		QTimer.singleShot(0, dialog.accept)
		exec_in_window(dialog, self.parent)
		self.assertIs(self.edit, QApplication.focusWidget())

	def test_prompt_focus_tab_and_enter_work_when_embedded(self):
		prompt = Prompt(
			self.parent, self.app, {}, 'Name', default='archive.tar.gz',
			selection_start=0, selection_end=7,
			get_completions=lambda _text: ['completed name']
		)
		line_edit = prompt._query
		observed = []
		def type_and_accept():
			QTest.qWait(10)
			observed.append((line_edit.hasFocus(), line_edit.selectedText()))
			QTest.keyClick(line_edit, Qt.Key_Tab)
			for _ in range(20):
				if line_edit.text() == 'completed name':
					break
				QTest.qWait(5)
			observed.append((line_edit.hasFocus(), line_edit.text()))
			QTest.keyClick(line_edit, Qt.Key_Return)
		QTimer.singleShot(0, type_and_accept)
		self.assertEqual(QDialog.Accepted, exec_in_window(prompt, self.parent))
		self.assertEqual(
			[(True, 'archive'), (True, 'completed name')], observed
		)
		self.assertEqual('completed name', prompt.textValue())


class _Window(QWidget):
	def focusNextPrevChild(self, _next):
		return False


class _DialogWithLineEdit(QDialog):
	def __init__(self):
		super().__init__()
		self.edit = QLineEdit(self)
		QVBoxLayout(self).addWidget(self.edit)
