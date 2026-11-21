from unittest import TestCase
from unittest.mock import patch

from core.commands import (
	ToggleCopyConfirmation, ToggleDeletePermanentlyConfirmation,
	ToggleMoveConfirmation, ToggleMoveToTrashConfirmation,
)
from core.commands.confirmations import (
	CONFIRM_COPY, CONFIRM_DELETE_PERMANENTLY, CONFIRM_MOVE,
	CONFIRM_MOVE_TO_TRASH, is_confirm_enabled, skip_prompt_destination,
)
from core.commands.force_transfer import ForceCopy
from core.commands.util import NO_SELECTION
from core.tests import StubUI
from core.tests.commands.test_transfer import ConfirmTreeOperationTest
from fman import OK, PLATFORM
from fman.url import as_url, join

import core.commands


class ConfirmationsTest(TestCase):
	def test_is_confirm_enabled_defaults_to_true(self):
		with patch(
			'core.commands.confirmations.get_setting', return_value=True
		) as get_setting:
			self.assertTrue(is_confirm_enabled(CONFIRM_COPY))
		get_setting.assert_called_once_with('Core Settings.json', CONFIRM_COPY, True)

	def test_toggle_commands_are_registered_and_switch_each_setting(self):
		commands = (
			(ToggleCopyConfirmation, CONFIRM_COPY, 'Toggle copy confirmation', 'Copy'),
			(ToggleMoveConfirmation, CONFIRM_MOVE, 'Toggle move confirmation', 'Move'),
			(ToggleMoveToTrashConfirmation, CONFIRM_MOVE_TO_TRASH,
			 'Toggle move to trash confirmation', 'Move to trash'),
			(ToggleDeletePermanentlyConfirmation, CONFIRM_DELETE_PERMANENTLY,
			 'Toggle delete permanently confirmation', 'Delete permanently'),
		)
		for command, key, alias, label in commands:
			with self.subTest(command=command.__name__), \
					patch('core.commands.confirmations.is_confirm_enabled',
						side_effect=(True, False)), \
					patch('core.commands.confirmations.save_setting') as save_setting, \
				patch(
					'core.commands.confirmations.show_status_message'
				) as show_status:
				self.assertIn(command.__name__, core.commands.__all__)
				self.assertEqual((alias,), command.aliases)
				instance = command(None)
				instance()
				instance()
			save_setting.assert_has_calls([
				(('Core Settings.json', key, False),),
				(('Core Settings.json', key, True),),
			])
			show_status.assert_has_calls([
				((label + ' confirmation: off',), {'timeout_secs': 3}),
				((label + ' confirmation: on',), {'timeout_secs': 3}),
			])

	def test_skip_destination_uses_existing_force_transfer_safety_checks(self):
		root = as_url('C:\\' if PLATFORM == 'Windows' else '/')
		source = join(root, 'source')
		file_ = join(source, 'file.txt')
		destination = join(root, 'destination')
		fs = ConfirmTreeOperationTest.FileSystem({
			source: {'is_dir': True}, file_: {'is_dir': False},
			destination: {'is_dir': True},
		})
		self.assertEqual(
			(destination, None),
			skip_prompt_destination(ForceCopy, [file_], destination, fs=fs),
		)

		ui = StubUI(self)
		ui.expect_alert((NO_SELECTION,), answer=OK)
		self.assertIsNone(skip_prompt_destination(ForceCopy, [], destination, ui, fs))
		ui.verify_expected_dialogs_were_shown()

		ui = StubUI(self)
		ui.expect_alert(('You cannot copy a file to itself!',), answer=OK)
		self.assertIsNone(
			skip_prompt_destination(ForceCopy, [source], join(source, 'child'), ui, fs)
		)
		ui.verify_expected_dialogs_were_shown()
