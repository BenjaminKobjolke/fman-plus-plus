import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from fman.impl.overwrite_dialog import (
	FileDetails, OverwriteChoice, OverwriteDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QDialog, QGridLayout, QLabel
from unittest import TestCase


_APP = QApplication.instance() or QApplication([])


class OverwriteDialogTest(TestCase):
	def setUp(self):
		self.dialog = OverwriteDialog(None, 'report.txt exists.', None)

	def tearDown(self):
		self.dialog.close()

	def test_buttons_are_grouped_in_four_rows(self):
		choices = (
			(OverwriteChoice.OVERWRITE, OverwriteChoice.OVERWRITE_ALL),
			(OverwriteChoice.RENAME, OverwriteChoice.RENAME_ALL),
			(OverwriteChoice.SKIP, OverwriteChoice.SKIP_ALL),
			(OverwriteChoice.ABORT,),
		)
		self.assertEqual(len(choices), len(self.dialog.button_rows))
		for row in self.dialog.button_rows:
			self.assertIsNotNone(row.itemAt(0).spacerItem())
			self.assertIsNotNone(row.itemAt(row.count() - 1).spacerItem())
		for row, row_choices in zip(self.dialog.button_rows, choices):
			self.assertEqual(
				[self.dialog.buttons[choice] for choice in row_choices],
				[row.itemAt(index).widget() for index in range(1, row.count() - 1)],
			)

	def test_right_and_left_move_in_reading_order_and_wrap(self):
		self.dialog.show()
		QApplication.processEvents()
		overwrite = self.dialog.buttons[OverwriteChoice.OVERWRITE]
		overwrite_all = self.dialog.buttons[OverwriteChoice.OVERWRITE_ALL]
		rename = self.dialog.buttons[OverwriteChoice.RENAME]
		abort = self.dialog.buttons[OverwriteChoice.ABORT]

		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Right)
		self.assertTrue(overwrite_all.hasFocus())
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Right)
		self.assertTrue(rename.hasFocus())

		overwrite.setFocus()
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Left)
		self.assertTrue(abort.hasFocus())
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Right)
		self.assertTrue(overwrite.hasFocus())

	def test_down_and_up_keep_the_column(self):
		self.dialog.show()
		QApplication.processEvents()
		overwrite = self.dialog.buttons[OverwriteChoice.OVERWRITE]
		overwrite_all = self.dialog.buttons[OverwriteChoice.OVERWRITE_ALL]
		rename_all = self.dialog.buttons[OverwriteChoice.RENAME_ALL]
		skip = self.dialog.buttons[OverwriteChoice.SKIP]
		skip_all = self.dialog.buttons[OverwriteChoice.SKIP_ALL]
		abort = self.dialog.buttons[OverwriteChoice.ABORT]

		overwrite_all.setFocus()
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Down)
		self.assertTrue(rename_all.hasFocus())
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Down)
		self.assertTrue(skip_all.hasFocus())
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Down)
		self.assertTrue(abort.hasFocus())
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Down)
		self.assertTrue(overwrite.hasFocus())

		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Up)
		self.assertTrue(abort.hasFocus())
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Up)
		self.assertTrue(skip.hasFocus())

	def test_enter_presses_the_focused_button(self):
		self.dialog.show()
		QApplication.processEvents()
		QTest.keyClick(QApplication.focusWidget(), Qt.Key_Down)
		button = self.dialog.buttons[OverwriteChoice.RENAME]
		self.assertTrue(button.hasFocus())
		QTest.keyClick(button, Qt.Key_Return)
		self.assertEqual(OverwriteChoice.RENAME, self.dialog.choice)
		self.assertEqual(QDialog.Accepted, self.dialog.result())

	def test_each_button_returns_its_choice(self):
		for choice in OverwriteChoice:
			with self.subTest(choice=choice):
				dialog = OverwriteDialog(None, 'exists', None)
				dialog.buttons[choice].click()
				self.assertEqual(QDialog.Accepted, dialog.result())
				self.assertEqual(choice, dialog.choice)
				dialog.close()

	def test_escape_returns_abort(self):
		QTest.keyClick(self.dialog, Qt.Key_Escape)
		self.assertEqual(OverwriteChoice.ABORT, self.dialog.choice)
		self.assertEqual(QDialog.Rejected, self.dialog.result())

	def test_overwrite_is_default_and_focused(self):
		button = self.dialog.buttons[OverwriteChoice.OVERWRITE]
		self.assertTrue(button.isDefault())
		self.dialog.show()
		QApplication.processEvents()
		self.assertTrue(button.hasFocus())

	def test_details_show_marks_and_optional_versions(self):
		details = (
			FileDetails('1 KB', 'Jan 1', '1.0.0.0'),
			FileDetails('2 KB', 'Jan 2', '2.0.0.0', True, True),
		)
		dialog = OverwriteDialog(None, 'exists', details)
		labels = [label.text() for label in dialog.findChildren(QLabel)]
		self.assertIn('2 KB (larger)', labels)
		self.assertIn('Jan 2 (newer)', labels)
		self.assertIn('1.0.0.0', labels)
		self.assertEqual(1, len(dialog.findChildren(QGridLayout)))
		dialog.close()

	def test_version_row_is_absent_when_no_versions_exist(self):
		details = (FileDetails('1 B', 'Today'), FileDetails('2 B', 'Yesterday'))
		dialog = OverwriteDialog(None, 'exists', details)
		labels = [label.text() for label in dialog.findChildren(QLabel)]
		self.assertNotIn('Version', labels)
		dialog.close()

	def test_absent_details_show_no_grid(self):
		self.assertEqual(0, len(self.dialog.findChildren(QGridLayout)))
		self.assertIn('report.txt exists.', [
			label.text() for label in self.dialog.findChildren(QLabel)
		])
