from fman.impl.clickable_path_setting import (
	CLICKABLE_PATH_OFF_MESSAGE, CLICKABLE_PATH_ON_MESSAGE,
	CLICKABLE_PATH_SETTING, ClickablePathSetting
)
from fman.impl.util.settings import Settings
from unittest import TestCase
from unittest.mock import MagicMock


class ClickablePathSettingTest(TestCase):
	def setUp(self):
		self.settings = MagicMock(spec=Settings)
		self.window = MagicMock(spec=['set_clickable_path'])

	def test_absent_setting_is_on_by_default(self):
		self.settings.get.return_value = True

		setting = ClickablePathSetting(self.settings)

		self.assertTrue(setting.is_enabled())
		self.settings.get.assert_called_once_with(CLICKABLE_PATH_SETTING, True)

	def test_explicit_false_disables_clickable_paths(self):
		self.settings.get.return_value = False

		self.assertFalse(ClickablePathSetting(self.settings).is_enabled())

	def test_toggle_off_persists_false_applies_and_reports_status(self):
		self.settings.get.side_effect = [True, False]

		message = ClickablePathSetting(self.settings).toggle(self.window)

		self.assertEqual(CLICKABLE_PATH_OFF_MESSAGE, message)
		self.settings.__setitem__.assert_called_once_with(CLICKABLE_PATH_SETTING, False)
		self.settings.flush.assert_called_once_with()
		self.window.set_clickable_path.assert_called_once_with(False)

	def test_toggle_on_removes_saved_false_applies_and_reports_status(self):
		self.settings.get.side_effect = [False, True]

		message = ClickablePathSetting(self.settings).toggle(self.window)

		self.assertEqual(CLICKABLE_PATH_ON_MESSAGE, message)
		self.settings.pop.assert_called_once_with(CLICKABLE_PATH_SETTING)
		self.settings.flush.assert_called_once_with()
		self.window.set_clickable_path.assert_called_once_with(True)

	def test_apply_sends_saved_value_to_window(self):
		self.settings.get.return_value = False

		ClickablePathSetting(self.settings).apply(self.window)

		self.window.set_clickable_path.assert_called_once_with(False)
