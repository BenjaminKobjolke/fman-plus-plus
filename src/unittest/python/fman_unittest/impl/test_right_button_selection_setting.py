from fman.impl.right_button_selection_setting import (
	RIGHT_BUTTON_SELECTION_OFF_MESSAGE, RIGHT_BUTTON_SELECTION_ON_MESSAGE,
	RIGHT_BUTTON_SELECTION_SETTING, RightButtonSelectionSetting
)
from fman.impl.util.settings import Settings
from unittest import TestCase
from unittest.mock import MagicMock


class RightButtonSelectionSettingTest(TestCase):
	def setUp(self):
		self.settings = MagicMock(spec=Settings)
		self.settings.get.return_value = False
		self.window = MagicMock(spec=['set_right_button_selection'])

	def test_absent_setting_is_off(self):
		setting = RightButtonSelectionSetting(self.settings)
		self.assertFalse(setting.is_enabled())
		self.settings.get.assert_called_once_with(RIGHT_BUTTON_SELECTION_SETTING, False)

	def test_non_boolean_value_is_off(self):
		self.settings.get.return_value = 1
		self.assertFalse(RightButtonSelectionSetting(self.settings).is_enabled())

	def test_toggle_enables_and_persists_true(self):
		self.settings.get.side_effect = [False, True]
		setting = RightButtonSelectionSetting(self.settings)
		self.assertEqual(RIGHT_BUTTON_SELECTION_ON_MESSAGE, setting.toggle(self.window))
		self.settings.__setitem__.assert_called_once_with(
			RIGHT_BUTTON_SELECTION_SETTING, True
		)
		self.window.set_right_button_selection.assert_called_once_with(True)
		self.settings.flush.assert_called_once_with()

	def test_toggle_back_removes_key_and_disables(self):
		self.settings.get.side_effect = [True, False]
		setting = RightButtonSelectionSetting(self.settings)
		self.assertEqual(
			RIGHT_BUTTON_SELECTION_OFF_MESSAGE, setting.toggle(self.window)
		)
		self.settings.pop.assert_called_once_with(RIGHT_BUTTON_SELECTION_SETTING)
		self.window.set_right_button_selection.assert_called_once_with(False)
		self.settings.flush.assert_called_once_with()
