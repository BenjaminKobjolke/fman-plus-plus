from unittest import TestCase
from unittest.mock import patch

from core.commands import ToggleDeselectAfterTransfer
from core.commands.deselect_after_transfer import \
	ToggleDeselectAfterTransfer as ToggleCommand


class ToggleDeselectAfterTransferTest(TestCase):
	def test_registered_command_toggles_setting_and_reports_state(self):
		self.assertIs(ToggleDeselectAfterTransfer, ToggleCommand)
		self.assertEqual(('Toggle deselect after copy',), ToggleCommand.aliases)
		with (
			patch(
				'core.commands.deselect_after_transfer.is_enabled',
				side_effect=(True, False)
			),
			patch('core.commands.deselect_after_transfer.save_setting') as save,
			patch(
				'core.commands.deselect_after_transfer.show_status_message'
			) as show_status,
		):
			command = ToggleCommand(None)
			command()
			command()
		save.assert_has_calls([
			(('Core Settings.json', 'deselect_after_transfer', False),),
			(('Core Settings.json', 'deselect_after_transfer', True),),
		])
		show_status.assert_has_calls([
			(('Deselect after copy: off',), {'timeout_secs': 3}),
			(('Deselect after copy: on',), {'timeout_secs': 3}),
		])
