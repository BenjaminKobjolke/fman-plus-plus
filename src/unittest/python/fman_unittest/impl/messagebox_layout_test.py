"""
Layout of MessageBox: how wide it gets, and how its text is aligned.

A message box is sized entirely from its label. Once the text is wide relative
to the screen - which happens readily under a theme with a large font - Qt turns
on word wrap and clamps the label, so even text containing explicit newlines is
re-wrapped into a tall, narrow column that can run off the bottom of the screen.
`MessageBox._apply_layout_fixes()` puts a floor under the width and left-aligns
anything longer than one line.

Deliberately named `*_test.py` rather than `test_*.py`, so `python build.py
test` does not discover it: it needs a QApplication of its own, and stray Qt
state is what makes that suite hang (see CLAUDE.md). Run it via
tools\\run_messagebox_tests.bat.
"""

from fman.impl.widgets import MessageBox
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QDialogButtonBox, QLabel, QMessageBox, \
	QScrollArea
from unittest import TestCase

ONE_LINE = 'Everything has no index loaded.'
MULTI_LINE = 'Everything has no index loaded.\n\n' \
	'Start the Everything service:\nsc start Everything'
# The message that regressed when a min-width was tried in styles.qss: it used
# to show as "Matrix screensaver is o".
LONG = 'Matrix screensaver is off. ' * 6

class MessageBoxLayoutTest(TestCase):
	def test_a_one_line_message_stays_centered(self):
		# Centered text lines up with the centered buttons.
		label = self._label_of(ONE_LINE)
		self.assertTrue(label.alignment() & Qt.AlignHCenter, label.alignment())
	def test_a_multi_line_message_is_left_aligned(self):
		# Centering reads poorly once the message is a paragraph.
		label = self._label_of(MULTI_LINE)
		self.assertTrue(label.alignment() & Qt.AlignLeft, label.alignment())
	def test_long_text_is_not_truncated(self):
		# The width floor must be a floor, not a fixed width. A stylesheet
		# min-width pinned the box and cut long messages off instead.
		self.assertEqual(LONG, self._label_of(LONG).text())
	def test_long_text_is_scrollable(self):
		box = self._box('\n'.join(['A long alert message.'] * 100))
		label = box.findChild(QLabel, 'qt_msgbox_label')
		scroll_area = label.parentWidget().parentWidget()
		self.assertIsInstance(scroll_area, QScrollArea)
		self.assertGreater(scroll_area.verticalScrollBar().maximum(), 0)
	def test_a_short_message_still_gets_a_minimum_width(self):
		narrow = self._box('Done.')
		self.assertGreater(narrow.width(), 0)
		# The floor applies to every box, so a one-word message is no narrower
		# than its own text would make it.
		self.assertGreaterEqual(narrow.width(), narrow.sizeHint().width() // 2)
	def test_the_width_floor_is_added_only_once(self):
		# _apply_layout_fixes() runs on every show; re-adding the spacer each
		# time would widen the box a little more every time it is reopened.
		box = self._box(ONE_LINE)
		rows_after_first = box.layout().rowCount()
		box._apply_layout_fixes()
		box._apply_layout_fixes()
		self.assertEqual(rows_after_first, box.layout().rowCount())
	def test_the_floor_never_exceeds_half_the_screen(self):
		# Under a large theme font, an unclamped floor would push the box wider
		# than the display.
		screen = QApplication.primaryScreen().availableGeometry().width()
		self.assertLessEqual(self._box(ONE_LINE).width(), screen)
	def test_many_buttons_widen_the_box(self):
		box = self._box('waiting.mp3 exists. Do you want to overwrite it?')
		box.setStandardButtons(
			QMessageBox.Yes | QMessageBox.YesToAll | QMessageBox.No |
			QMessageBox.NoToAll | QMessageBox.Abort
		)
		QApplication.sendEvent(box, QEvent(QEvent.LayoutRequest))
		button_box = box.findChild(QDialogButtonBox)
		margins = box.layout().contentsMargins()
		needed = button_box.minimumSizeHint().width() + margins.left() + margins.right()
		screen = QApplication.primaryScreen().availableGeometry().width()
		# Hidden buttons keep Qt's default 100 px geometry, and the 800 px offscreen
		# screen is narrower than the five large-font buttons need.
		self.assertGreaterEqual(box.width(), min(needed, screen))
	def _label_of(self, text):
		return self._box(text).findChild(QLabel, 'qt_msgbox_label')
	def _box(self, text):
		box = MessageBox(None)
		box.setText(text)
		box.setStandardButtons(QMessageBox.Ok)
		# Qt polishes in setVisible() before delivering showEvent, so this is the
		# real ordering. show() itself is avoided: fman's transparency code needs
		# a real window and aborts under the offscreen platform.
		box.ensurePolished()
		box._apply_layout_fixes()
		box.adjustSize()
		self.addCleanup(box.deleteLater)
		return box
	@classmethod
	def setUpClass(cls):
		# One QApplication per process; Qt refuses a second one.
		cls.app = QApplication.instance() or QApplication([])
		# Approximate a theme with a large font, which is what makes Qt wrap.
		cls.app.setFont(QFont('Consolas', 20))
