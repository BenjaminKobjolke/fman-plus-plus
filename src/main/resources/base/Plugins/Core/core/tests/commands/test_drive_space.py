from unittest import TestCase
from unittest.mock import patch

from core.commands.drive_space import _get_refresh_seconds, _should_refresh


class GetRefreshSecondsTest(TestCase):
	def test_absent_setting_uses_default(self):
		with patch('core.commands.drive_space.get_setting', return_value=10):
			self.assertEqual(10, _get_refresh_seconds())

	def test_valid_values_are_used(self):
		for value in (0, 30):
			with self.subTest(value=value), \
					patch('core.commands.drive_space.get_setting', return_value=value):
				self.assertEqual(value, _get_refresh_seconds())

	def test_invalid_values_use_default(self):
		for value in (-1, '30', True, None):
			with self.subTest(value=value), \
					patch('core.commands.drive_space.get_setting', return_value=value):
				self.assertEqual(10, _get_refresh_seconds())


class ShouldRefreshTest(TestCase):
	def test_only_refreshes_drives_with_a_positive_interval(self):
		self.assertTrue(_should_refresh('drives://', 10))
		self.assertFalse(_should_refresh('file://C:/', 10))
		self.assertFalse(_should_refresh('drives://', 0))
