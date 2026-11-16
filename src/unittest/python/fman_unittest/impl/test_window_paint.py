"""Tests for composing fman's native windows into a desktop screenshot."""

from fman.impl.scripting.window_paint import compose_screen
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QApplication
from unittest import TestCase


_APP = QApplication.instance() or QApplication([])


class WindowPaintTest(TestCase):
	def test_compose_screen_places_layers_in_screen_coordinates_and_order(self):
		background = QPixmap(100, 100)
		background.fill(QColor('red'))
		blue = QPixmap(20, 20)
		blue.fill(QColor('blue'))
		green = QPixmap(20, 20)
		green.fill(QColor('green'))
		layers = [
			(QRect(1010, 10, 20, 20), blue.toImage()),
			(QRect(1020, 20, 20, 20), green.toImage()),
		]

		result = compose_screen(background, QRect(1000, 0, 100, 100), layers)

		image = result.toImage()
		self.assertEqual(QColor('blue'), image.pixelColor(15, 15))
		self.assertEqual(QColor('green'), image.pixelColor(25, 25))
		self.assertEqual(QColor('red'), image.pixelColor(5, 5))
