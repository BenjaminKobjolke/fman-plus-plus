from core.undo_history import CopyRecord, MoveRecord, RenameRecord, TrashRecord, history
from core.commands.undo import Undo
from fman import DirectoryPane, Task
from unittest import TestCase
from unittest.mock import MagicMock, patch


class UndoTest(TestCase):
	def setUp(self):
		history.clear()
		self.pane = MagicMock(spec=DirectoryPane)

	def tearDown(self):
		history.clear()

	def _undo(self, record=None):
		if record is not None:
			history.record(record)
		return Undo(self.pane)

	def test_empty_history_reports_nothing_to_undo(self):
		with patch('core.commands.undo.show_alert') as alert:
			self._undo()()
		alert.assert_called_once_with('Nothing to undo.')

	def test_trash_undo_is_not_supported_outside_windows(self):
		with patch('core.commands.undo.PLATFORM', 'Linux'), \
				patch('core.commands.undo.show_alert') as alert:
			self._undo(TrashRecord(('file:///a.txt',)))()
		alert.assert_called_once_with(
			'Restoring from the Trash is only supported on Windows. '
			'Nothing was restored.'
		)
		self.assertIsNone(history.pop())

	def test_windows_trash_restore_uses_recycle_bin_and_notifies_pane(self):
		entry = object()
		with patch('core.commands.undo.PLATFORM', 'Windows'), \
				patch(
					'core.commands.undo.find_entry', return_value=entry
				) as find, \
				patch('core.commands.undo.restore_entry') as restore, \
				patch('core.commands.undo.notify_file_added') as added:
			self._undo(TrashRecord(('file:///a.txt',)))()
		find.assert_called_once_with('file:///a.txt')
		restore.assert_called_once_with(entry)
		added.assert_called_once_with('file:///a.txt')

	def test_trash_restore_aggregates_failures(self):
		with patch('core.commands.undo.PLATFORM', 'Windows'), \
				patch(
					'core.commands.undo.find_entry',
					side_effect=[object(), None]
				), \
				patch(
					'core.commands.undo.restore_entry',
					side_effect=FileExistsError('original file exists')
				), \
				patch('core.commands.undo.show_alert') as alert:
			self._undo(TrashRecord(('file:///a.txt', 'file:///b.txt')))()
		self.assertIn('a.txt', alert.call_args.args[0])
		self.assertIn('b.txt', alert.call_args.args[0])

	def test_move_skips_when_original_path_has_another_file(self):
		pair = ('file:///old/a.txt', 'file:///new/a.txt')
		with patch(
			'core.commands.undo.exists', side_effect=lambda url: url == pair[0]
		), \
				patch('core.commands.undo.samefile', return_value=False), \
				patch('core.commands.undo.prepare_move') as move, \
				patch('core.commands.undo.show_alert') as alert:
			self._undo(MoveRecord((pair,)))()
		move.assert_not_called()
		self.assertIn('occupied', alert.call_args.args[0])

	def test_case_only_rename_can_move_back_and_places_cursor(self):
		pair = ('file://C:/dir/Foo', 'file://C:/dir/foo')
		with patch('core.commands.undo.exists', return_value=True), \
				patch('core.commands.undo.samefile', return_value=True), \
				patch('core.commands.undo.elevation.move', return_value=False), \
				patch('core.commands.undo.prepare_move', return_value=[]) as move, \
				patch(
					'core.commands.undo.submit_task',
					side_effect=lambda task: task()
				):
			self._undo(RenameRecord((pair,)))()
		move.assert_called_once_with(pair[1], pair[0])
		self.pane.place_cursor_at.assert_called_once_with(pair[0])

	def test_copy_confirms_before_trashing_remaining_destinations(self):
		pair = ('file:///src/a.txt', 'file:///dest/a.txt')
		with patch('core.commands.undo.exists', return_value=True), \
				patch(
					'core.commands.undo.confirm_trash', return_value=True
				) as confirm, \
				patch('core.commands.undo.trash') as trash:
			self._undo(CopyRecord((pair,)))()
		confirm.assert_called_once_with([pair[1]])
		trash.assert_called_once_with([pair[1]], undoable=False)

	def test_declined_copy_confirmation_leaves_copy_in_place(self):
		pair = ('file:///src/a.txt', 'file:///dest/a.txt')
		with patch('core.commands.undo.exists', return_value=True), \
				patch('core.commands.undo.confirm_trash', return_value=False), \
				patch('core.commands.undo.trash') as trash:
			self._undo(CopyRecord((pair,)))()
		trash.assert_not_called()
		self.assertEqual(CopyRecord((pair,)), history.pop())

	def test_copy_undo_ignores_destinations_that_are_already_gone(self):
		pair = ('file:///src/a.txt', 'file:///dest/a.txt')
		with patch('core.commands.undo.exists', return_value=False), \
				patch('core.commands.undo.confirm_trash') as confirm:
			self._undo(CopyRecord((pair,)))()
		confirm.assert_not_called()

	def test_move_uses_elevation_for_protected_original_path(self):
		pair = ('file://C:/Program Files/a.txt', 'file:///dest/a.txt')
		with patch(
			'core.commands.undo.exists', side_effect=lambda url: url == pair[1]
		), \
				patch(
					'core.commands.undo.elevation.move', return_value=True
				) as elevated, \
				patch('core.commands.undo.prepare_move') as move:
			self._undo(MoveRecord((pair,)))()
		elevated.assert_called_once_with(
			[pair[1]], 'file://C:/Program Files', 'a.txt'
		)
		move.assert_not_called()

	def test_move_back_failure_is_reported_without_moving_cursor(self):
		pair = ('file:///old/a.txt', 'file:///new/a.txt')
		def fail_move():
			raise OSError('disk unavailable')
		with patch(
			'core.commands.undo.exists', side_effect=lambda url: url == pair[1]
		), \
				patch('core.commands.undo.elevation.move', return_value=False), \
				patch(
					'core.commands.undo.prepare_move',
					return_value=[Task('Moving', fn=fail_move)]
				), \
				patch(
					'core.commands.undo.submit_task', side_effect=lambda task: task()
				), \
				patch('core.commands.undo.show_alert') as alert:
			self._undo(MoveRecord((pair,)))()
		self.assertIn('disk unavailable', alert.call_args.args[0])
		self.pane.place_cursor_at.assert_not_called()

