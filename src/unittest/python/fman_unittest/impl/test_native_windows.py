import os
from unittest import TestCase, skipUnless
from unittest.mock import patch

from PyQt5.QtCore import QRect

from fman.impl.native_windows import (
	own_dialog_windows, own_windows_top_to_bottom, screen_index_at,
)


class NativeWindowsTest(TestCase):
	def setUp(self):
		self.screens = [QRect(0, 0, 100, 100), QRect(100, 0, 100, 100)]

	def test_finds_screen_containing_rectangle_center(self):
		self.assertEqual(0, screen_index_at(QRect(10, 10, 20, 20), self.screens))
		self.assertEqual(1, screen_index_at(QRect(120, 10, 20, 20), self.screens))

	def test_straddling_rectangle_uses_screen_containing_center(self):
		self.assertEqual(1, screen_index_at(QRect(82, 10, 40, 20), self.screens))

	def test_offscreen_rectangle_uses_nearest_screen(self):
		self.assertEqual(1, screen_index_at(QRect(250, 10, 20, 20), self.screens))

	def test_no_screens_returns_none(self):
		self.assertIsNone(screen_index_at(QRect(0, 0, 10, 10), []))

	@skipUnless(os.name == 'nt', 'native windows are Windows-only')
	def test_own_windows_keep_enum_order_and_dialog_api(self):
		import win32gui
		import win32process
		main, foreign, dialog_one, dialog_two, invisible_dialog = range(1, 6)
		handles = [main, foreign, dialog_one, dialog_two, invisible_dialog]
		visible = {main, foreign, dialog_one, dialog_two}
		classes = {
			main: 'FmanWindow', foreign: '#32770', dialog_one: '#32770',
			dialog_two: '#32770', invisible_dialog: '#32770',
		}
		process_ids = {
			main: os.getpid(), foreign: os.getpid() + 1,
			dialog_one: os.getpid(), dialog_two: os.getpid(),
			invisible_dialog: os.getpid(),
		}
		with (
			patch.object(win32gui, 'EnumWindows',
				lambda callback, extra: [callback(hwnd, extra) for hwnd in handles]),
			patch.object(win32gui, 'IsWindowVisible',
				lambda hwnd: hwnd in visible),
			patch.object(win32gui, 'GetClassName', lambda hwnd: classes[hwnd]),
			patch.object(win32process, 'GetWindowThreadProcessId',
				lambda hwnd: (0, process_ids[hwnd])),
		):
			self.assertEqual(
				[main, dialog_one, dialog_two],
				own_windows_top_to_bottom(main),
			)
			self.assertEqual({dialog_one, dialog_two}, own_dialog_windows())
