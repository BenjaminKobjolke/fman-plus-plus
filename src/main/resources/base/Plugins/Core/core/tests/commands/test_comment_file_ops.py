from core.commands import deletion, rename, show_file_comment_error, transfer
from core.commands.undo import Undo
from core.undo_history import CopyRecord, MoveRecord, TrashRecord, history
from fman import DirectoryPane
from unittest import TestCase
from unittest.mock import Mock, patch


class CommentErrorReportingTest(TestCase):
	def test_comment_error_uses_the_shared_status_message(self):
		with patch('fman.show_status_message') as status:
			show_file_comment_error(OSError('disk full'))
		status.assert_called_once_with(
			'Could not update file comments: disk full'
		)


class CommentTransferTest(TestCase):
	_SRC = 'file:///src/a.txt'
	_DST = 'file:///dst/a.txt'

	def setUp(self):
		history.clear()

	def tearDown(self):
		history.clear()

	def test_copy_carries_comments_to_successful_destinations(self):
		with patch('core.commands.transfer.copy_comments') as copy_comments, \
				patch('core.commands.transfer.fman.fs.exists', return_value=True):
			transfer.Copy(Mock(spec=DirectoryPane))._record_operation(
				((self._SRC, self._DST),), set()
			)
		copy_comments.assert_called_once_with(((self._SRC, self._DST),))
		self.assertEqual(CopyRecord(((self._SRC, self._DST),)), history.pop())

	def test_move_carries_comments_only_when_source_disappeared(self):
		with patch('core.commands.transfer.move_comments') as move_comments, \
				patch(
					'core.commands.transfer.fman.fs.exists',
					side_effect=lambda url: url == self._DST
				):
			transfer.Move(Mock(spec=DirectoryPane))._record_operation(
				((self._SRC, self._DST),), set()
			)
		move_comments.assert_called_once_with(((self._SRC, self._DST),))
		self.assertEqual(MoveRecord(((self._SRC, self._DST),)), history.pop())

	def test_comment_write_failure_does_not_fail_copy(self):
		with patch(
			'core.commands.transfer.copy_comments', side_effect=OSError('disk full')
		), patch('core.commands.transfer.fman.fs.exists', return_value=True), \
				patch('core.commands.transfer.show_file_comment_error') as alert:
			transfer.Copy(Mock(spec=DirectoryPane))._record_operation(
				((self._SRC, self._DST),), set()
			)
		self.assertEqual(CopyRecord(((self._SRC, self._DST),)), history.pop())
		alert.assert_called_once()
		self.assertEqual('disk full', str(alert.call_args.args[0]))

	def test_copy_uses_the_auto_renamed_destination(self):
		renamed = 'file:///dst/a (2).txt'
		with patch(
			'core.commands.transfer.copy_comments'
		) as copy_comments, patch(
			'core.commands.transfer.fman.fs.exists', return_value=True
		):
			transfer.Copy(Mock(spec=DirectoryPane))._record_operation(
				((self._SRC, renamed),), set()
			)
		copy_comments.assert_called_once_with(((self._SRC, renamed),))

	def test_move_keeps_comment_when_source_still_exists(self):
		with patch('core.commands.transfer.move_comments') as move_comments, \
				patch('core.commands.transfer.fman.fs.exists', return_value=True):
			transfer.Move(Mock(spec=DirectoryPane))._record_operation(
				((self._SRC, self._DST),), set()
			)
		move_comments.assert_not_called()


class CommentRenameTest(TestCase):
	def test_rename_moves_comment(self):
		pair = ('file:///dir/old.txt', 'file:///dir/new.txt')
		with patch('core.commands.rename.move_comments') as move_comments:
			rename._record_rename(*pair)
		move_comments.assert_called_once_with((pair,))

	def test_comment_failure_does_not_prevent_rename_undo_record(self):
		pair = ('file:///dir/old.txt', 'file:///dir/new.txt')
		with patch(
			'core.commands.rename.move_comments', side_effect=OSError('read only')
		), patch('core.commands.rename.show_file_comment_error') as status:
			rename._record_rename(*pair)
		status.assert_called_once()
		self.assertEqual('read only', str(status.call_args.args[0]))


class CommentDeletionTest(TestCase):
	def test_trash_removes_comments_and_records_them_for_undo(self):
		url = 'file:///dir/a.txt'
		comment = (url, 'remember me')
		with patch('core.commands.deletion.elevation.delete', return_value=True), \
				patch('core.commands.deletion.exists', return_value=False), \
				patch(
					'core.commands.deletion.remove_comments',
					return_value=[comment]
			) as remove_comments:
			deletion.trash([url])
		remove_comments.assert_called_once_with((url,))
		self.assertEqual(TrashRecord((url,), (comment,)), history.pop())

	def test_permanent_delete_removes_comments_after_success(self):
		url = 'file:///dir/a.txt'
		with patch('core.commands.deletion.elevation.delete', return_value=True), \
				patch('core.commands.deletion.exists', return_value=False), \
				patch('core.commands.deletion.remove_comments') as remove_comments:
			deletion.delete([url])
		remove_comments.assert_called_once_with((url,))

	def test_comment_failure_does_not_fail_delete(self):
		url = 'file:///dir/a.txt'
		with patch('core.commands.deletion.elevation.delete', return_value=True), \
				patch('core.commands.deletion.exists', return_value=False), \
				patch(
					'core.commands.deletion.remove_comments',
					side_effect=OSError('read only')
			), patch('core.commands.deletion.show_file_comment_error') as status:
			deletion.delete([url])
		status.assert_called_once()
		self.assertEqual('read only', str(status.call_args.args[0]))


class CommentUndoTest(TestCase):
	def setUp(self):
		history.clear()
		self.pane = Mock(spec=DirectoryPane)

	def tearDown(self):
		history.clear()

	def test_undo_move_moves_comment_back_after_file_move(self):
		pair = ('file:///old/a.txt', 'file:///new/a.txt')
		with patch('core.commands.undo.PLATFORM', 'Linux'), \
				patch(
					'core.commands.undo.exists',
					side_effect=lambda url: url == pair[1]
				), patch('core.commands.undo.elevation.move', return_value=True), \
				patch('core.commands.undo.move_comments') as move_comments:
			Undo(self.pane)._undo_moves(MoveRecord((pair,)))
		move_comments.assert_called_once_with(((pair[1], pair[0]),))

	def test_undo_trash_restores_saved_comments(self):
		url = 'file:///a.txt'
		comment = (url, 'remember me')
		with patch('core.commands.undo.PLATFORM', 'Windows'), \
				patch('core.commands.undo.find_entry', return_value=object()), \
				patch('core.commands.undo.restore_entry'), \
				patch('core.commands.undo.notify_file_added'), \
				patch('core.commands.undo.restore_comments') as restore_comments:
			Undo(self.pane)._undo_trash(TrashRecord((url,), (comment,)))
		restore_comments.assert_called_once_with((comment,))

	def test_comment_failure_does_not_fail_trash_undo(self):
		url = 'file:///a.txt'
		comment = (url, 'remember me')
		with patch('core.commands.undo.PLATFORM', 'Windows'), \
				patch('core.commands.undo.find_entry', return_value=object()), \
				patch('core.commands.undo.restore_entry'), \
				patch('core.commands.undo.notify_file_added'), \
				patch(
					'core.commands.undo.restore_comments',
					side_effect=OSError('read only')
				), patch('core.commands.undo.show_file_comment_error') as status:
			Undo(self.pane)._undo_trash(TrashRecord((url,), (comment,)))
		status.assert_called_once()
		self.assertEqual('read only', str(status.call_args.args[0]))

