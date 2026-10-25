"""A long status message must not set the main window's minimum width."""

from fman.impl.widgets import MainWindow
from PyQt5.QtWidgets import QApplication
from unittest import TestCase


class StatusBarTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def test_long_message_does_not_widen_the_minimum_window(self):
		window = MainWindow(None, [], None, None, None, None)
		self.addCleanup(window.deleteLater)
		window.ensurePolished()
		window.show_status_message('Ready.')
		window._status_bar.layout().activate()
		minimum_width = window.minimumSizeHint().width()

		window.show_status_message('x' * 500)
		window._status_bar.layout().activate()

		self.assertEqual(minimum_width, window.minimumSizeHint().width())

	def test_incognito_marker_stays_visible_with_status_messages(self):
		window = MainWindow(None, [], None, None, None, None)
		self.addCleanup(window.deleteLater)
		marker = window._incognito_marker

		self.assertTrue(marker.isHidden())
		window.set_incognito_marker_visible(True)
		self.assertFalse(marker.isHidden())

		window.show_status_message('Copied to clipboard.')

		self.assertFalse(marker.isHidden())
		self.assertEqual('Incognito', marker.text())
		window.set_incognito_marker_visible(False)
		self.assertTrue(marker.isHidden())
