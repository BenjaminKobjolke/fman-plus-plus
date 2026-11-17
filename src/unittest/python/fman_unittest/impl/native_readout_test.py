"""Tests for the scripting API's native window readout."""

import os
from types import SimpleNamespace
from unittest import TestCase, skipUnless
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMainWindow

from fman.impl.scripting.native_readout import NativeReadout


class NativeReadoutTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def _snapshot(self, window):
		return NativeReadout(window, SimpleNamespace(get_panes=lambda: [])).snapshot()

	def test_snapshot_reports_the_qt_window_title(self):
		window = QMainWindow()
		window.setWindowTitle('left | right - fman')
		self.addCleanup(window.close)
		with patch('fman.impl.scripting.native_readout.own_dialog_windows',
				return_value=[]):
			result = self._snapshot(window)
		self.assertEqual('left | right - fman', result['window_title'])

	@skipUnless(os.name == 'nt', 'The taskbar caption is Windows-only.')
	def test_snapshot_reports_the_windows_taskbar_caption(self):
		import win32gui

		window = QMainWindow()
		self.addCleanup(window.close)
		with patch('fman.impl.scripting.native_readout.own_dialog_windows',
				return_value=[]), patch.object(
			win32gui, 'GetWindowText', return_value='left - fman') as get_window_text:
			result = self._snapshot(window)
		self.assertEqual('left - fman', result['taskbar_title'])
		get_window_text.assert_called_once_with(int(window.winId()))

	def test_snapshot_omits_taskbar_title_off_windows(self):
		window = QMainWindow()
		self.addCleanup(window.close)
		with patch('fman.impl.scripting.native_readout.os.name', 'posix'), patch(
			'fman.impl.scripting.native_readout.own_dialog_windows',
			return_value=[],
		):
			result = self._snapshot(window)
		self.assertIsNone(result['taskbar_title'])
