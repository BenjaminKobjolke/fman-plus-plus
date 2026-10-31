from fman.impl.tray import should_hide_on_minimize, should_show_tray_icon
from unittest import TestCase


class TrayVisibilityTest(TestCase):
	def test_minimize_is_hidden_only_when_the_setting_is_enabled(self):
		self.assertTrue(should_hide_on_minimize(True))
		self.assertFalse(should_hide_on_minimize(False))

	def test_icon_is_visible_when_minimize_to_tray_is_enabled(self):
		self.assertTrue(should_show_tray_icon(True, False))

	def test_icon_is_visible_while_hidden_when_setting_is_disabled(self):
		self.assertTrue(should_show_tray_icon(False, True))

	def test_icon_is_hidden_when_setting_is_disabled_and_window_is_visible(self):
		self.assertFalse(should_show_tray_icon(False, False))
