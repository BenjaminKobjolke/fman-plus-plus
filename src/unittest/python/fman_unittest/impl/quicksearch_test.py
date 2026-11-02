from unittest import TestCase

from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QFont, QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QWidget

from fman.impl.quicksearch import Quicksearch
from fman.impl.quicksearch_elide import elide_title_left, shift_highlight


class QuicksearchTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.parent = QWidget()
		self.parent.resize(1600, 900)
		self.parent.setStyleSheet('QListView { min-width: 400px; }')
		self.parent.show()
		self.app.processEvents()
		self.dialog = Quicksearch(
			self.parent, _StubApp(), {}, lambda _query: []
		)
		self.app.processEvents()

	def tearDown(self):
		self.dialog.close()
		self.parent.close()
		self.app.processEvents()

	def test_shift_highlight_drops_hidden_chars_and_moves_visible_chars(self):
		self.assertEqual([2, 3], shift_highlight([0, 1, 10, 11], 9))
		self.assertEqual([3], shift_highlight([3], 0))

	def test_elide_title_left_leaves_a_fitting_title_unchanged(self):
		font = QFont()
		shown, removed = elide_title_left('short', font, 1000)
		self.assertEqual(('short', 0), (shown, removed))

	def test_elide_title_left_keeps_the_end_of_an_overlong_title(self):
		font = QFont()
		shown, removed = elide_title_left('a very long folder name', font, 130)
		self.assertTrue(shown.startswith('…'))
		self.assertTrue(shown.endswith('name'))
		self.assertGreater(removed, 0)

	def test_elide_title_left_accepts_a_fractional_width(self):
		font = QFont()
		shown, removed = elide_title_left('a very long folder name', font, 130.5)
		self.assertTrue(shown.startswith('…'))
		self.assertTrue(shown.endswith('name'))
		self.assertGreater(removed, 0)

	def test_resize_to_widens_and_keeps_the_dialog_centered(self):
		default_width = self.dialog.width()
		center = self.dialog.x() + default_width / 2
		self.dialog._resize_to(default_width + 200)
		self.assertEqual(default_width + 200, self.dialog.width())
		self.assertEqual(center, self.dialog.x() + self.dialog.width() / 2)

	def test_resize_to_can_shrink_back_to_default_after_widening(self):
		default_width = self.dialog.width()
		self.dialog._resize_to(default_width + 200)
		self.dialog._resize_to(default_width)
		self.assertEqual(default_width, self.dialog.width())

	def test_resize_to_does_not_shrink_below_default(self):
		default_width = self.dialog.width()
		self.dialog._resize_to(default_width - 100)
		self.assertEqual(default_width, self.dialog.width())

	def test_resize_to_caps_at_parent_width(self):
		self.dialog._resize_to(5000)
		self.assertEqual(self.parent.width(), self.dialog.width())

	def test_dragging_right_grip_widens_by_twice_the_drag_distance(self):
		self.dialog.show()
		self.app.processEvents()
		start_width = self.dialog.width()
		grip = self.dialog._right_grip
		start = grip.rect().center()
		QTest.mousePress(grip, Qt.LeftButton, pos=start)
		self.assertIsNotNone(grip._start_x)
		move_to = start + QPoint(40, 0)
		global_x = grip._start_x + 40
		global_y = grip.mapToGlobal(start).y()
		global_pos = QPointF(global_x, global_y)
		QTest.mouseMove(grip, move_to)
		# Offscreen QtTest moves the cursor but may omit the held-button move.
		move_event = QMouseEvent(
			QEvent.MouseMove, QPointF(move_to), global_pos, Qt.NoButton,
			Qt.LeftButton, Qt.NoModifier
		)
		self.app.sendEvent(grip, move_event)
		self.assertEqual(start_width + 80, self.dialog.width())
		release_pos = grip.mapFromGlobal(QPoint(global_x, global_y))
		QTest.mouseRelease(grip, Qt.LeftButton, pos=release_pos)
		self.app.processEvents()
		self.assertEqual(start_width + 2 * 40, self.dialog.width())


class _StubApp:
	def exit(self, _code):
		pass
