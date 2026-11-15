"""Tests for placing the Windows shell Properties dialogs near the pane."""

from unittest import TestCase, skipUnless
from unittest.mock import MagicMock, patch

from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtWidgets import QApplication, QWidget

from core.commands import properties_placement as placement
from fman import PLATFORM


@skipUnless(PLATFORM == 'Windows', 'Windows shell command')
class PropertiesPlacementTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def test_target_point_uses_row_bottom_left(self):
		self.assertEqual(
			placement.target_point(QRect(20, 30, 100, 40), QRect(0, 0, 500, 400)),
			QPoint(20, 69),
		)

	def test_target_point_falls_back_to_pane_inset(self):
		self.assertEqual(
			placement.target_point(None, QRect(100, 200, 500, 400)),
			QPoint(140, 240),
		)

	def test_clamp_to_screen_keeps_rect_inside(self):
		rect = QRect(120, 130, 100, 80)
		self.assertEqual(
			placement.clamp_to_screen(rect, QRect(0, 0, 500, 400)), QPoint(120, 130)
		)

	def test_clamp_to_screen_pulls_right_and_bottom_edges_in(self):
		self.assertEqual(
			placement.clamp_to_screen(QRect(450, 350, 100, 80), QRect(0, 0, 500, 400)),
			QPoint(400, 320),
		)

	def test_clamp_to_screen_pushes_left_and_top_edges_in(self):
		self.assertEqual(
			placement.clamp_to_screen(QRect(-20, -30, 100, 80), QRect(0, 0, 500, 400)),
			QPoint(0, 0),
		)

	def test_clamp_to_screen_aligns_oversized_rect_with_negative_monitor(self):
		self.assertEqual(
			placement.clamp_to_screen(
				QRect(-1500, -100, 2000, 1200), QRect(-1280, 0, 1280, 1024)
			),
			QPoint(-1280, 0),
		)

	def test_watch_moves_only_new_dialogs_and_cascades_them(self):
		pane = MagicMock()
		pane._widget = QWidget()
		self.addCleanup(pane._widget.deleteLater)
		with patch.object(
			placement,
			'_pane_placement',
			return_value=(QPoint(100, 200), QRect(0, 0, 1000, 800)),
		), patch.object(placement, 'own_dialog_windows', return_value={10}):
			placer = placement.PropertiesPlacer(pane, expected=2)
		placer.watch()
		win32gui = MagicMock(spec=placement.win32gui)
		win32gui.GetWindowRect.side_effect = lambda hwnd: (0, 0, 100, 80)
		with patch.object(
			placement, 'own_dialog_windows', return_value={10, 11, 12}
		), \
				patch.object(placement, 'win32gui', win32gui):
			placer._poll()

		self.assertEqual(win32gui.SetWindowPos.call_count, 2)
		self.assertEqual(win32gui.SetWindowPos.call_args_list[0].args[2:4], (100, 200))
		self.assertEqual(win32gui.SetWindowPos.call_args_list[1].args[2:4], (130, 230))
		self.assertFalse(placer._timer.isActive())

	def test_watch_stops_after_timeout_without_moving_dialogs(self):
		pane = MagicMock()
		pane._widget = QWidget()
		self.addCleanup(pane._widget.deleteLater)
		with patch.object(
			placement,
			'_pane_placement',
			return_value=(QPoint(100, 200), QRect(0, 0, 1000, 800)),
		), patch.object(placement, 'own_dialog_windows', return_value=set()):
			placer = placement.PropertiesPlacer(pane, expected=1)
		placer.watch()
		placer._started_at = 1.0
		win32gui = MagicMock(spec=placement.win32gui)
		with patch.object(
			placement, 'own_dialog_windows', return_value=set()
		), \
				patch.object(placement, 'win32gui', win32gui), \
				patch.object(placement.time, 'monotonic', return_value=4.1):
			placer._poll()

		win32gui.SetWindowPos.assert_not_called()
		self.assertFalse(placer._timer.isActive())
