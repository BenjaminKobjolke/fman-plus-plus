from unittest import TestCase
from unittest.mock import patch

from core.commands import SetAutomaticUpdateInterval, ToggleAutomaticUpdates
from core.commands.auto_update import (
	SetAutomaticUpdateInterval as SetIntervalCommand,
	ToggleAutomaticUpdates as ToggleCommand,
)


class AutomaticUpdateCommandsTest(TestCase):
	def test_registered_commands_and_aliases(self):
		self.assertIs(ToggleAutomaticUpdates, ToggleCommand)
		self.assertIs(SetAutomaticUpdateInterval, SetIntervalCommand)
		self.assertEqual(('Toggle automatic updates',), ToggleCommand.aliases)
		self.assertEqual(
			('Set automatic update interval',), SetIntervalCommand.aliases
		)

	def test_toggle_saves_setting_and_reports_state(self):
		with (
			patch('core.commands.auto_update.is_supported', return_value=True),
			patch('core.commands.auto_update.is_enabled', side_effect=(False, True)),
			patch('core.commands.auto_update.save_setting') as save_setting,
			patch('core.commands.auto_update.show_status_message') as show_status,
		):
			command = ToggleCommand(None)
			command()
			command()
		save_setting.assert_has_calls([
			(('Core Settings.json', 'auto_update', True),),
			(('Core Settings.json', 'auto_update', False),),
		])
		show_status.assert_has_calls([
			(('Automatic updates: on',), {'timeout_secs': 3}),
			(('Automatic updates: off',), {'timeout_secs': 3}),
		])

	def test_unsupported_copy_explains_toggle_is_unavailable(self):
		with (
			patch('core.commands.auto_update.is_supported', return_value=False),
			patch('core.commands.auto_update.save_setting') as save_setting,
			patch('core.commands.auto_update.show_alert') as show_alert,
		):
			ToggleCommand(None)()
		save_setting.assert_not_called()
		show_alert.assert_called_once_with(
			'Automatic updates only work with the installed Windows version.'
		)

	def test_interval_prompt_saves_valid_value(self):
		with (
			patch('core.commands.auto_update.is_supported', return_value=True),
			patch('core.commands.auto_update.interval_hours', return_value=24),
			patch(
				'core.commands.auto_update.show_prompt',
				return_value=('12', True),
			) as show_prompt,
			patch('core.commands.auto_update.save_setting') as save_setting,
			patch('core.commands.auto_update.show_alert') as show_alert,
		):
			SetIntervalCommand(None)()
		show_prompt.assert_called_once_with(
			'Automatic update interval in hours (1–720):', '24'
		)
		save_setting.assert_called_once_with(
			'Core Settings.json', 'auto_update_interval_hours', 12
		)
		show_alert.assert_not_called()

	def test_invalid_interval_is_rejected(self):
		with (
			patch('core.commands.auto_update.is_supported', return_value=True),
			patch('core.commands.auto_update.interval_hours', return_value=24),
			patch(
				'core.commands.auto_update.show_prompt',
				return_value=('721', True),
			),
			patch('core.commands.auto_update.save_setting') as save_setting,
			patch('core.commands.auto_update.show_alert') as show_alert,
		):
			SetIntervalCommand(None)()
		save_setting.assert_not_called()
		show_alert.assert_called_once_with(
			'Enter an interval from 1 to 720 hours.'
		)

	def test_non_numeric_interval_is_rejected(self):
		with (
			patch('core.commands.auto_update.is_supported', return_value=True),
			patch('core.commands.auto_update.interval_hours', return_value=24),
			patch(
				'core.commands.auto_update.show_prompt',
				return_value=('hourly', True),
			),
			patch('core.commands.auto_update.save_setting') as save_setting,
			patch('core.commands.auto_update.show_alert') as show_alert,
		):
			SetIntervalCommand(None)()
		save_setting.assert_not_called()
		show_alert.assert_called_once_with(
			'Enter an interval from 1 to 720 hours.'
		)

	def test_cancelled_interval_prompt_does_not_change_setting(self):
		with (
			patch('core.commands.auto_update.is_supported', return_value=True),
			patch('core.commands.auto_update.interval_hours', return_value=24),
			patch(
				'core.commands.auto_update.show_prompt',
				return_value=('', False),
			),
			patch('core.commands.auto_update.save_setting') as save_setting,
			patch('core.commands.auto_update.show_alert') as show_alert,
		):
			SetIntervalCommand(None)()
		save_setting.assert_not_called()
		show_alert.assert_not_called()

	def test_unsupported_copy_explains_interval_is_unavailable(self):
		with (
			patch('core.commands.auto_update.is_supported', return_value=False),
			patch('core.commands.auto_update.show_prompt') as show_prompt,
			patch('core.commands.auto_update.show_alert') as show_alert,
		):
			SetIntervalCommand(None)()
		show_prompt.assert_not_called()
		show_alert.assert_called_once_with(
			'Automatic updates only work with the installed Windows version.'
		)
