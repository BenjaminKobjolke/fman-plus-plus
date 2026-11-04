from core.commands import ToggleReadOnlyReplaceQuestion
from core.commands.read_only_overwrite import (
	ToggleReadOnlyReplaceQuestion as ToggleCommand,
)
from unittest import TestCase
from unittest.mock import patch


class ToggleReadOnlyReplaceQuestionTest(TestCase):
	def test_registered_command_toggles_setting_and_reports_state(self):
		self.assertIs(ToggleReadOnlyReplaceQuestion, ToggleCommand)
		self.assertEqual(
			('Toggle read-only replace question',), ToggleCommand.aliases
		)
		with (
			patch(
				'core.commands.read_only_overwrite.is_enabled',
				side_effect=(True, False)
			),
			patch('core.commands.read_only_overwrite.save_setting') as save_setting,
			patch(
				'core.commands.read_only_overwrite.show_status_message'
			) as show_status,
		):
			command = ToggleCommand(None)
			command()
			command()
		save_setting.assert_has_calls([
			(('Core Settings.json', 'ask_before_replacing_read_only', False),),
			(('Core Settings.json', 'ask_before_replacing_read_only', True),),
		])
		show_status.assert_has_calls([
			(('Read-only replace question: off',), {'timeout_secs': 3}),
			(('Read-only replace question: on',), {'timeout_secs': 3}),
		])
