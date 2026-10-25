from core.commands import deletion
from core.commands.deletion import _describe, DeletePermanently
from core.undo_history import TrashRecord, history
from fman import DirectoryPane, PLATFORM, Task, YES
from fman.url import as_url
from unittest import TestCase
from unittest.mock import Mock, patch

class TrashTest(TestCase):
	def setUp(self):
		history.clear()

	def tearDown(self):
		history.clear()

	def test_trash_records_only_local_files_that_are_gone(self):
		urls = ['file:///a.txt', 'ftp://host/b.txt']
		with patch('core.commands.deletion.elevation.delete', return_value=True), \
				patch('core.commands.deletion.exists', side_effect=[False]), \
				patch('core.commands.deletion.history.record') as record:
			deletion.trash(urls)
		record.assert_called_once_with(TrashRecord(('file:///a.txt',)))

	def test_trash_can_skip_recording_for_undo(self):
		with patch('core.commands.deletion.elevation.delete', return_value=True), \
				patch('core.commands.deletion.exists') as exists, \
				patch('core.commands.deletion.history.record') as record:
			deletion.trash(['file:///a.txt'], undoable=False)
		exists.assert_not_called()
		record.assert_not_called()

	def test_trash_does_not_record_files_that_still_exist(self):
		with patch('core.commands.deletion.elevation.delete', return_value=True), \
				patch('core.commands.deletion.exists', return_value=True), \
				patch('core.commands.deletion.history.record') as record:
			deletion.trash(['file:///a.txt'])
		record.assert_not_called()

	def test_trash_with_unsupported_url_deletes_nothing(self):
		urls = ['file://C:/a.zip', 'zip://C:/a.zip/report.txt']
		local_task = Mock(spec=Task)
		local_task.get_size.return_value = 1
		def prepare_trash(url):
			if url.startswith('zip://'):
				raise NotImplementedError()
			return [local_task]
		with patch('core.commands.deletion.prepare_trash',
				 side_effect=prepare_trash), \
			 patch('core.commands.deletion.prepare_delete',
				 side_effect=AssertionError('Permanent delete fallback')), \
			 patch('core.commands.deletion.exists', return_value=True), \
			 patch('core.commands.deletion.submit_task') as submit_task, \
			 patch('core.commands.deletion.elevation.delete', return_value=False):
			deletion.trash(urls)
		delete_task = submit_task.call_args.args[0]
		with patch.object(delete_task, 'run') as run, \
			 patch.object(delete_task, 'show_alert') as show_alert:
			delete_task()
		run.assert_not_called()
		trash_name = 'Recycle Bin' if PLATFORM == 'Windows' else 'Trash'
		show_alert.assert_called_once_with(
			'The %s is not available in zip://. Nothing was deleted. '
			'Use Delete permanently instead.' % trash_name
		)
	def test_delete_permanently_reports_unsupported_filesystem(self):
		with patch('core.commands.deletion.show_alert', return_value=YES), \
			 patch('core.commands.deletion.elevation.delete', return_value=False), \
				 patch('core.commands.deletion.submit_task') as submit_task, \
				 patch('core.commands.deletion.prepare_delete',
					 side_effect=NotImplementedError):
			DeletePermanently(Mock(spec=DirectoryPane))(
				urls=['zip://archive.zip/file.txt']
			)
		delete_task = submit_task.call_args.args[0]
		with patch.object(delete_task, 'show_alert') as show_alert:
			delete_task()
		show_alert.assert_called_once_with(
			'Deleting files in zip:// is not supported.'
		)

	def test_confirm_delete_uses_permanent_delete_wording_and_returns_result(self):
		urls = ['file:///a.txt']
		message = (
			'Do you really want to PERMANENTLY delete a.txt? This action '
			'cannot be undone!'
		)
		with patch('core.commands.deletion.show_alert', return_value=YES) as alert:
			self.assertTrue(deletion.confirm_delete(urls))
		alert.assert_called_once_with(message, deletion.YES | deletion.NO, deletion.YES)
		with patch('core.commands.deletion.show_alert', return_value=deletion.NO):
			self.assertFalse(deletion.confirm_delete(urls))

	def test_delete_uses_elevation_then_submits_background_task_when_needed(self):
		urls = ['file:///a.txt']
		with patch(
			'core.commands.deletion.elevation.delete', return_value=False,
		) as elevated, \
				patch('core.commands.deletion.submit_task') as submit_task:
			deletion.delete(urls)
		elevated.assert_called_once_with(urls, to_trash=False)
		task = submit_task.call_args.args[0]
		self.assertEqual(urls, task._urls)
		self.assertIs(deletion.prepare_delete, task._prepare_fn)

	def test_delete_skips_background_task_when_elevation_succeeds(self):
		with patch('core.commands.deletion.elevation.delete', return_value=True), \
				patch('core.commands.deletion.submit_task') as submit_task:
			deletion.delete(['file:///a.txt'])
		submit_task.assert_not_called()

class DescribeTest(TestCase):

	"""
	`_describe` names a single file but only counts several, and the caller
	picks the wording of the count ('these %d files' in a confirmation, the
	default '%d files' in a task title).
	"""

	def test_one_file_is_named_not_counted(self):
		self.assertEqual('a.txt', _describe([as_url('/dir/a.txt')]))
	def test_several_files_are_counted_with_the_default_template(self):
		self.assertEqual('2 files', _describe(self._urls('a', 'b')))
	def test_the_template_is_applied(self):
		self.assertEqual(
			'these 3 items',
			_describe(self._urls('a', 'b', 'c'), 'these %d items')
		)
	def test_the_template_is_ignored_for_a_single_file(self):
		self.assertEqual(
			'a', _describe(self._urls('a'), 'these %d items')
		)
	def _urls(self, *names):
		return [as_url('/dir/' + name) for name in names]
