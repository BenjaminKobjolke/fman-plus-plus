from core.commands.force_transfer import ForceCopy, ForceMove
from core.commands.util import NO_SELECTION
from core.tests import StubUI
from core.tests.commands.test_transfer import ConfirmTreeOperationTest
from fman import OK, PLATFORM
from fman.url import as_url, join
from unittest import TestCase
from unittest.mock import Mock


class ForceTransferTest(TestCase):
	FileSystem = ConfirmTreeOperationTest.FileSystem

	def setUp(self):
		self._root = as_url('C:\\' if PLATFORM == 'Windows' else '/')
		self._src = join(self._root, 'src')
		self._dest = join(self._root, 'dest')
		self._file = join(self._src, 'file.txt')
		self._folder = join(self._src, 'folder')
		self._fs = self.FileSystem({
			self._src: {'is_dir': True},
			self._dest: {'is_dir': True},
			self._file: {'is_dir': False},
			self._folder: {'is_dir': True},
		})

	def test_copy_one_file_uses_destination_without_prompt(self):
		self._assert_uses_destination(ForceCopy, [self._file])

	def test_copy_several_files_uses_destination_without_prompt(self):
		self._assert_uses_destination(ForceCopy, [self._file, self._folder])

	def test_no_files_shows_no_selection_alert(self):
		ui = StubUI(self)
		ui.expect_alert((NO_SELECTION,), answer=OK)
		self.assertIsNone(
			ForceCopy._confirm_tree_operation([], self._dest, ui, self._fs)
		)
		ui.verify_expected_dialogs_were_shown()

	def test_copy_folder_into_itself_is_rejected(self):
		self._assert_rejects_folder_into_itself(ForceCopy, 'copy')

	def test_move_folder_into_itself_is_rejected(self):
		self._assert_rejects_folder_into_itself(ForceMove, 'move')

	def test_queue_titles_keep_copy_and_move_verbs(self):
		transfers = (('file:///src/file.txt', 'file:///dest/file.txt'),)
		self.assertTrue(ForceCopy._queue_title(transfers).startswith('Copy '))
		self.assertTrue(ForceMove._queue_title(transfers).startswith('Move '))

	def _assert_uses_destination(self, command, files):
		ui = Mock()
		self.assertEqual(
			(self._dest, None),
			command._confirm_tree_operation(files, self._dest, ui, self._fs)
		)
		ui.show_input.assert_not_called()
		ui.show_alert.assert_not_called()

	def _assert_rejects_folder_into_itself(self, command, verb):
		ui = StubUI(self)
		ui.expect_alert(
			('You cannot %s a file to itself!' % verb,), answer=OK
		)
		self.assertIsNone(
			command._confirm_tree_operation(
				[self._src], self._folder, ui, self._fs
			)
		)
		ui.verify_expected_dialogs_were_shown()

