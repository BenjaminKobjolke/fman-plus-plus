from unittest import TestCase
from unittest.mock import Mock, patch

from core.transfer_queue import is_enabled, run_queued
from core.commands import ToggleTransferQueue
from core.commands.transfer_queue import ToggleTransferQueue as ToggleCommand


class TransferQueueSettingTest(TestCase):
	def test_queue_is_enabled_by_default(self):
		with patch('core.transfer_queue.get_setting', return_value=True) as get_setting:
			self.assertTrue(is_enabled())
		get_setting.assert_called_once_with(
			'Core Settings.json', 'queue_transfers', True
		)

	def test_run_queued_dispatches_to_public_api_when_enabled(self):
		work = Mock()
		with (
			patch('core.transfer_queue.is_enabled', return_value=True),
			patch('fman.run_in_transfer_queue', return_value=True) as run,
		):
			self.assertTrue(run_queued('Copy item', work))
		run.assert_called_once_with('Copy item', work)

	def test_run_queued_calls_work_directly_when_disabled(self):
		work = Mock(return_value='done')
		with (
			patch('core.transfer_queue.is_enabled', return_value=False),
			patch('fman.run_in_transfer_queue') as run,
		):
			self.assertEqual('done', run_queued('Copy item', work))
		run.assert_not_called()
		work.assert_called_once_with()

	def test_registered_command_toggles_setting_and_reports_state(self):
		self.assertIs(ToggleTransferQueue, ToggleCommand)
		self.assertEqual(('Toggle transfer queue',), ToggleCommand.aliases)
		with (
			patch('core.commands.transfer_queue.is_enabled', side_effect=(True, False)),
			patch('core.commands.transfer_queue.save_setting') as save_setting,
			patch('core.commands.transfer_queue.show_status_message') as show_status,
		):
			command = ToggleCommand(None)
			command()
			command()
		save_setting.assert_has_calls([
			(('Core Settings.json', 'queue_transfers', False),),
			(('Core Settings.json', 'queue_transfers', True),),
		])
		show_status.assert_has_calls([
			(('Transfer queue: off',), {'timeout_secs': 3}),
			(('Transfer queue: on',), {'timeout_secs': 3}),
		])
