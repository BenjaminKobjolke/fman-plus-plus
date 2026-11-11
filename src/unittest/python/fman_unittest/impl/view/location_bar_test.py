"""Location bar interaction tests use a QApplication of their own."""

from fman.impl.view.location_bar import LocationBar
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication
from unittest import TestCase


class LocationBarTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def setUp(self):
		self.bar = LocationBar()
		self.bar.resize(360, 30)
		self.bar.set_location('zip://root/parent/current')
		self.bar.show()
		self.app.processEvents()
		self.segment_clicks = []
		self.go_to_clicks = []
		self.bar.segment_clicked.connect(self.segment_clicks.append)
		self.bar.clicked.connect(lambda: self.go_to_clicks.append(True))
		self.addCleanup(self.bar.deleteLater)

	def test_clicking_parent_folder_emits_its_url(self):
		self._click_text('parent')

		self.assertEqual(['zip://root/parent'], self.segment_clicks)
		self.assertEqual([], self.go_to_clicks)

	def test_clicking_current_folder_opens_go_to(self):
		self._click_text('current')

		self.assertEqual([], self.segment_clicks)
		self.assertEqual([True], self.go_to_clicks)

	def test_clicking_space_after_path_opens_go_to(self):
		self._click(self.bar.width() - 4)

		self.assertEqual([], self.segment_clicks)
		self.assertEqual([True], self.go_to_clicks)

	def test_disabled_clickable_path_opens_go_to_for_parent(self):
		self.bar.set_clickable(False)

		self._click_text('parent')

		self.assertEqual([], self.segment_clicks)
		self.assertEqual([True], self.go_to_clicks)

	def test_hovering_parent_folder_shows_pointing_hand(self):
		self._move_to_text('parent')

		self.assertEqual(Qt.PointingHandCursor, self.bar.cursor().shape())

	def test_hovering_current_folder_restores_arrow_cursor(self):
		self._move_to_text('parent')
		self._move_to_text('current')

		self.assertEqual(Qt.ArrowCursor, self.bar.cursor().shape())

	def _click_text(self, text):
		self._click(self._text_position(text))

	def _move_to_text(self, text):
		self._send_mouse(QEvent.MouseMove, self._text_position(text), Qt.NoButton)

	def _text_position(self, text):
		index = self.bar.text().index(text) + len(text) // 2
		y = self.bar.height() // 2
		for x in range(self.bar.width()):
			if self.bar.cursorPositionAt(QPoint(x, y)) == index:
				return x
		self.fail('Text position is not visible in the location bar')

	def _click(self, x):
		self._send_mouse(QEvent.MouseButtonPress, x, Qt.LeftButton)

	def _send_mouse(self, event_type, x, button):
		pos = QPoint(x, self.bar.height() // 2)
		QApplication.sendEvent(self.bar, QMouseEvent(
			event_type, QPointF(pos), button,
			button if button != Qt.NoButton else Qt.NoButton,
			Qt.NoModifier
		))
