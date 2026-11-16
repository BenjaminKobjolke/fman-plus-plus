from unittest import TestCase

from PyQt5.QtCore import QRect

from fman.impl.native_windows import screen_index_at


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
