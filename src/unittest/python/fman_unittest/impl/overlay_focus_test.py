"""
Keyboard behaviour of the tutorial's Overlay: which button has focus, how the
user moves between them and what Enter does.

Deliberately named `*_test.py` rather than `test_*.py`, so `python build.py
test` does not discover it: it needs a QApplication of its own, and stray Qt
state is what makes that suite hang (see CLAUDE.md). Run it via
tools\\run_overlay_focus_tests.bat.
"""

from fman.impl.overlay import Overlay
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, \
	QWidget
from unittest import TestCase

class OverlayFocusTest(TestCase):
	def test_affirmative_button_starts_focused(self):
		self._show_overlay(takes_focus=True)
		self.assertEqual('&Yes', self._focused().text())
	def test_enter_activates_the_focused_button(self):
		self._show_overlay(takes_focus=True)
		QTest.keyClick(self._focused(), Qt.Key_Return)
		self.assertEqual(['yes'], self.clicked)
	def test_arrow_keys_move_between_the_buttons(self):
		self._show_overlay(takes_focus=True)
		for key, expected in (
			# Left/Up go back, Right/Down forward, both wrapping around:
			(Qt.Key_Left, '&No'), (Qt.Key_Right, '&Yes'),
			(Qt.Key_Down, '&No'), (Qt.Key_Up, '&Yes')
		):
			QTest.keyClick(self._focused(), key)
			self.assertEqual(expected, self._focused().text(), key)
	def test_enter_activates_a_button_reached_by_arrow_key(self):
		self._show_overlay(takes_focus=True)
		QTest.keyClick(self._focused(), Qt.Key_Left)
		QTest.keyClick(self._focused(), Qt.Key_Return)
		self.assertEqual(['no'], self.clicked)
	def test_buttons_have_alt_letter_shortcuts(self):
		# They work no matter where focus is. Delivering Alt+N here would need
		# a truly active window, which the offscreen platform does not give us,
		# so check the shortcut Qt derived from the label instead.
		overlay = self._show_overlay(takes_focus=True)
		self.assertEqual(
			[QKeySequence('Alt+N'), QKeySequence('Alt+Y')],
			[b.shortcut() for b in overlay.findChildren(QPushButton)]
		)
	def test_closing_hands_focus_back(self):
		overlay = self._show_overlay(takes_focus=True)
		overlay.close()
		self._process_events()
		self.assertIs(self.edit, self._focused())
	def test_without_takes_focus_the_pane_keeps_the_keyboard(self):
		self._show_overlay(takes_focus=False)
		self.assertIs(self.edit, self._focused())
		QTest.keyClick(self.edit, Qt.Key_Return)
		self.assertEqual([], self.clicked)
	def setUp(self):
		self.clicked = []
		# One QApplication per process; Qt refuses a second one.
		self.app = QApplication.instance() or QApplication([])
		self.window = QWidget()
		self.edit = QLineEdit(self.window)
		QVBoxLayout(self.window).addWidget(self.edit)
		self.window.resize(600, 400)
		self.window.show()
		self._process_events()
		self.window.activateWindow()
		self.edit.setFocus()
		self._process_events()
	def tearDown(self):
		self.window.close()
		self._process_events()
	def _show_overlay(self, takes_focus):
		result = Overlay(
			self.window, 'Take the tour?',
			[
				('&No', lambda: self.clicked.append('no')),
				('&Yes', lambda: self.clicked.append('yes'))
			],
			takes_focus
		)
		result.show()
		self._process_events()
		return result
	def _focused(self):
		return QApplication.focusWidget()
	def _process_events(self):
		self.app.processEvents()
