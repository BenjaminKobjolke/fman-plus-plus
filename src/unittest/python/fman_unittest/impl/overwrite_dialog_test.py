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

	def test_has_four_buttons_in_first_row_and_three_in_second(self):
		self.assertEqual(4, self.dialog.button_rows[0].count())
		self.assertEqual(3, self.dialog.button_rows[1].count())

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
