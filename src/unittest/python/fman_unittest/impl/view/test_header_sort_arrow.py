from PyQt5.QtCore import QRect
from unittest import TestCase

from fman.impl.view.header_sort_arrow import (
	SortArrowPosition, place_sort_arrow,
)


class SortArrowPositionTest(TestCase):
	def test_from_setting(self):
		self.assertEqual(
			SortArrowPosition.from_setting('after'), SortArrowPosition.AFTER,
		)
		self.assertEqual(
			SortArrowPosition.from_setting('before'), SortArrowPosition.BEFORE,
		)
		self.assertEqual(SortArrowPosition.from_setting('edge'), SortArrowPosition.EDGE)
		for value in (None, '', 'left', 3):
			with self.subTest(value=value):
				self.assertEqual(
					SortArrowPosition.from_setting(value), SortArrowPosition.AFTER,
				)

	def test_place_after_text(self):
		label = QRect(10, 0, 200, 20)
		arrow = QRect(220, 5, 10, 10)

		placement = place_sort_arrow(
			SortArrowPosition.AFTER, label, 40, arrow, 4,
		)

		self.assertEqual(placement.arrow, QRect(54, 5, 10, 10))
		self.assertEqual(placement.label, label)

	def test_after_falls_back_when_text_is_elided(self):
		label = QRect(10, 0, 200, 20)
		arrow = QRect(220, 5, 10, 10)

		placement = place_sort_arrow(SortArrowPosition.AFTER, label, 210, arrow, 4)

		self.assertEqual(placement.arrow, arrow)
		self.assertEqual(placement.label, label)

	def test_after_clamps_arrow_at_qt_default_position(self):
		label = QRect(10, 0, 200, 20)
		arrow = QRect(220, 5, 10, 10)

		placement = place_sort_arrow(SortArrowPosition.AFTER, label, 200, arrow, 4)

		self.assertEqual(placement.arrow, arrow)

	def test_place_before_text(self):
		label = QRect(10, 0, 200, 20)
		arrow = QRect(220, 5, 10, 10)

		placement = place_sort_arrow(SortArrowPosition.BEFORE, label, 40, arrow, 4)

		self.assertEqual(placement.arrow, QRect(10, 5, 10, 10))
		self.assertEqual(placement.label, QRect(24, 0, 186, 20))

	def test_before_falls_back_when_text_does_not_fit(self):
		label = QRect(10, 0, 200, 20)
		arrow = QRect(220, 5, 10, 10)

		placement = place_sort_arrow(SortArrowPosition.BEFORE, label, 190, arrow, 4)

		self.assertEqual(placement.arrow, arrow)
		self.assertEqual(placement.label, label)

	def test_edge_keeps_qt_rectangles(self):
		label = QRect(10, 0, 200, 20)
		arrow = QRect(220, 5, 10, 10)

		placement = place_sort_arrow(SortArrowPosition.EDGE, label, 40, arrow, 4)

		self.assertEqual(placement.arrow, arrow)
		self.assertEqual(placement.label, label)
