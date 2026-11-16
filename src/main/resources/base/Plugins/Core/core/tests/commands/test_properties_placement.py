"""Tests for placing the Windows shell Properties dialogs near the pane."""

import gc
import threading
import time
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

	def test_watch_keeps_placer_alive_until_new_dialog_is_positioned(self):
		pane = MagicMock()
		pane._widget = QWidget()
		self.addCleanup(pane._widget.deleteLater)
		win32gui = MagicMock(spec=placement.win32gui)
		win32gui.GetWindowRect.return_value = (0, 0, 100, 80)
		dialogs = [set(), {123}]

		def start_and_release_placer():
			placer = placement.PropertiesPlacer(pane, expected=1)
			placer.watch()
			return placer._timer

		with patch.object(
			placement,
			'_pane_placement',
			return_value=(QPoint(600, 400), QRect(0, 0, 1200, 900)),
		), patch.object(
			placement, 'own_dialog_windows',
			side_effect=lambda: dialogs[-1] if len(dialogs) == 1
				else dialogs.pop(0),
		), patch.object(placement, 'win32gui', win32gui):
			timer = start_and_release_placer()
			gc.collect()
			self.addCleanup(timer.stop)
			deadline = time.monotonic() + 2
			while win32gui.SetWindowPos.call_count == 0 and time.monotonic() < deadline:
				QApplication.processEvents()
				time.sleep(0.01)

		self.assertEqual(win32gui.SetWindowPos.call_count, 1)
		self.assertEqual(win32gui.SetWindowPos.call_args.args[2:4], (600, 400))

	def test_placer_built_on_worker_thread_runs_its_timer_on_main_thread(self):
		pane = MagicMock()
		pane._widget = QWidget()
		self.addCleanup(pane._widget.deleteLater)
		placers = []
		errors = []

		def build_placer():
			try:
				placer = placement.PropertiesPlacer(pane, expected=1)
				placer.watch()
				placers.append(placer)
			except Exception as error:
				errors.append(error)

		with patch.object(
			placement,
			'_pane_placement',
			return_value=(QPoint(100, 200), QRect(0, 0, 1000, 800)),
		), patch.object(placement, 'own_dialog_windows', return_value=set()):
			worker = threading.Thread(target=build_placer, daemon=True)
			worker.start()
			deadline = time.monotonic() + 5
			while worker.is_alive() and time.monotonic() < deadline:
				QApplication.processEvents()
				worker.join(0.01)

		self.assertFalse(worker.is_alive(), 'worker did not finish')
		if errors:
			raise errors[0]
		self.assertEqual(len(placers), 1)
		placer = placers[0]
		self.addCleanup(placer._timer.stop)
		self.assertIs(placer._timer.thread(), QApplication.instance().thread())
		self.assertTrue(placer._timer.isActive())
