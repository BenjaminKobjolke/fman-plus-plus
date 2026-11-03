from unittest import TestCase

from fman.impl.scroll_margin_setting import load_scroll_margin


class ScrollMarginSettingTest(TestCase):
	def test_missing_setting_defaults_to_zero(self):
		self.assertEqual(load_scroll_margin({}), 0)

	def test_non_negative_integer_is_used(self):
		self.assertEqual(load_scroll_margin({'scroll_margin': 3}), 3)
		self.assertEqual(load_scroll_margin({'scroll_margin': 0}), 0)

	def test_invalid_values_default_to_zero(self):
		for value in (-1, '3', True, 2.5):
			with self.subTest(value=value):
				self.assertEqual(load_scroll_margin({'scroll_margin': value}), 0)
