from unittest import TestCase
from unittest.mock import patch

from core.commands import ToggleLockedFileCheck
from core.commands.locked_files import ToggleLockedFileCheck as ToggleCommand


class ToggleLockedFileCheckTest(TestCase):
	def test_registered_command_toggles_setting_and_reports_state(self):
		self.assertIs(ToggleLockedFileCheck, ToggleCommand)
		self.assertEqual(('Toggle locked file check',), ToggleCommand.aliases)
		with (
			patch('core.commands.locked_files.is_enabled', side_effect=(True, False)),
			patch('core.commands.locked_files.save_setting') as save_setting,
			patch('core.commands.locked_files.show_status_message') as show_status,
		):
			command = ToggleCommand(None)
			command()
			command()
		save_setting.assert_has_calls([
			(('Core Settings.json', 'check_locked_files', False),),
			(('Core Settings.json', 'check_locked_files', True),),
		])
		show_status.assert_has_calls([
			(('Locked file check: off',), {'timeout_secs': 3}),
			(('Locked file check: on',), {'timeout_secs': 3}),
		])
