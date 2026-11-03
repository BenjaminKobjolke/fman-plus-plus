"""Countdown dialog behavior, tested without showing a native window."""

from fman.impl.countdown import Countdown
from PyQt5.QtWidgets import QApplication, QProgressBar
from unittest import TestCase

_APP = QApplication.instance() or QApplication([])

class CountdownTest(TestCase):
	def test_tick_updates_text_and_progress(self):
		countdown = Countdown(None, 'Updating in %d seconds', 3)
		self.addCleanup(countdown.deleteLater)
		progress = countdown.findChild(QProgressBar)
		self.assertEqual('Updating in 3 seconds', countdown.text())
		self.assertEqual(3, progress.value())
		countdown._tick()
		self.assertEqual('Updating in 2 seconds', countdown.text())
		self.assertEqual(2, progress.value())

	def test_tick_finishes_with_ok_at_zero(self):
		countdown = Countdown(None, 'Updating in %d seconds', 1)
		self.addCleanup(countdown.deleteLater)
		results = []
		countdown.finished.connect(results.append)
		countdown._tick()
		self.assertEqual([countdown.Ok], results)

	def test_cancel_button_cancels(self):
		countdown = Countdown(None, 'Updating in %d seconds', 3)
		self.addCleanup(countdown.deleteLater)
		results = []
		countdown.finished.connect(results.append)
		self.assertIs(
			countdown.button(countdown.Cancel), countdown.defaultButton()
		)
		countdown.button(countdown.Cancel).click()
		self.assertEqual([countdown.Cancel], results)
		self.assertFalse(countdown._timer.isActive())
