from fman.impl.model.overlay_compose import compose_overlay
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import QApplication
from unittest import TestCase

_APP = QApplication.instance() or QApplication([])


class ComposeOverlayTest(TestCase):

	def test_composes_overlay_at_each_supported_size(self):
		icon = QIcon()
		icon.addPixmap(_pixmap(48, 'blue'))
		overlay = _pixmap(48, 'red')

		composed = compose_overlay(icon, overlay)

		for size in (16, 32, 48):
			with self.subTest(size=size):
				image = composed.pixmap(QSize(size, size)).toImage()
				self.assertEqual(
					QColor('blue'), image.pixelColor(size - 1, size - 1)
				)
				self.assertEqual(
					QColor('red'), image.pixelColor(size // 4, size - 1)
				)
				self.assertEqual(QColor('blue'), image.pixelColor(size - 1, 0))

	def test_empty_overlay_returns_original_icon(self):
		icon = QIcon()
		icon.addPixmap(_pixmap(32, 'blue'))

		self.assertIs(icon, compose_overlay(icon, QPixmap()))


def _pixmap(size, color):
	pixmap = QPixmap(size, size)
	pixmap.fill(QColor(color))
	return pixmap
