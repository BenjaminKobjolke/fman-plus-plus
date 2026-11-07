"""Tests for command visibility, selection, locking and plug-in discovery."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

from robocopy_plugin import CopyWithRobocopy, MoveWithRobocopy, _invoke
from robocopy_plugin import _lock
from fman.impl.plugins.discover import find_plugin_dirs
from fman.url import as_human_readable


class CommandTest(TestCase):
	def setUp(self):
		self.pane = Mock()
		self.pane.window.get_panes.return_value = [self.pane, Mock()]
		patcher = patch(
			'robocopy_plugin._queue_enabled', return_value=False, create=True
		)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_commands_are_visible_only_on_windows(self):
		with patch('robocopy_plugin.PLATFORM', 'Windows'):
			self.assertTrue(CopyWithRobocopy(self.pane).is_visible())
			self.assertTrue(MoveWithRobocopy(self.pane).is_visible())
		with patch('robocopy_plugin.PLATFORM', 'Linux'):
			self.assertFalse(CopyWithRobocopy(self.pane).is_visible())
			self.assertFalse(MoveWithRobocopy(self.pane).is_visible())

	def test_names_and_aliases_are_stable(self):
		self.assertEqual(('Copy with robocopy',), CopyWithRobocopy(self.pane).aliases)
		self.assertEqual(('Move with robocopy',), MoveWithRobocopy(self.pane).aliases)

	def test_invoke_submits_the_plan_and_refreshes_both_panes(self):
		other = self.pane.window.get_panes.return_value[1]
		self.pane.get_path.return_value = 'file:///C:/source'
		self.pane.get_selected_files.return_value = ['file:///C:/source/file.txt']
		self.pane.window.get_panes.return_value = [self.pane, other]
		other.get_path.return_value = 'file:///C:/other'
		plan = Mock(jobs=())
		with patch(
			'robocopy_plugin.fman.show_input', return_value='C:\\dest'
		), \
				patch(
					'robocopy_plugin._queue_enabled', return_value=False, create=True
				), \
				patch('robocopy_plugin.fman.load_json', return_value={}), \
				patch(
					'robocopy_plugin.windows.executable',
					return_value='C:\\Windows\\robocopy.exe'
				), \
				patch(
					'robocopy_plugin.planner.prepare', return_value=plan
				) as prepare, \
				patch('robocopy_plugin.planner.probe') as probe, \
				patch('robocopy_plugin.fman.submit_task') as submit:
			_invoke('move', MoveWithRobocopy(self.pane))
		self.assertTrue(prepare.call_args.kwargs['move'])
		self.assertEqual('C:\\dest', prepare.call_args.args[2])
		probe.assert_called_once()
		submit.assert_called_once()
		self.pane.reload.assert_called_once_with()
		other.reload.assert_called_once_with()

	def test_prompt_defaults_to_the_other_panes_folder(self):
		other = self.pane.window.get_panes.return_value[1]
		other.get_path.return_value = 'file:///C:/other'
		self.pane.get_selected_files.return_value = ['file:///C:/source/file.txt']
		with patch(
			'robocopy_plugin.fman.show_input', return_value=None
		) as prompt:
			_invoke('copy', CopyWithRobocopy(self.pane))
		self.assertEqual(
			as_human_readable('file:///C:/other'), prompt.call_args.args[1]
		)
		self.assertEqual(0, prompt.call_args.args[2])
		self.assertIsNone(prompt.call_args.args[3])

	def test_canceling_or_accepting_an_empty_prompt_starts_nothing(self):
		self.pane.window.get_panes.return_value[1].get_path.return_value = 'file:///C:/other'
		self.pane.get_selected_files.return_value = ['file:///C:/source/file.txt']
		for response in [None, '']:
			with self.subTest(response=response):
				with patch(
					'robocopy_plugin._queue_enabled', return_value=False, create=True
				), \
						patch(
							'robocopy_plugin.fman.show_input', return_value=response
						), \
						patch('robocopy_plugin.planner.prepare') as prepare, \
						patch('robocopy_plugin.fman.submit_task') as submit:
					_invoke('copy', CopyWithRobocopy(self.pane))
			prepare.assert_not_called()
			submit.assert_not_called()

	def test_no_selection_stops_before_showing_the_destination_prompt(self):
		self.pane.get_selected_files.return_value = []
		self.pane.get_file_under_cursor.return_value = None
		with patch('robocopy_plugin.fman.show_alert') as alert, \
				patch('robocopy_plugin.fman.show_input') as prompt:
			_invoke('copy', CopyWithRobocopy(self.pane))
		alert.assert_called_once()
		prompt.assert_not_called()

	@patch('robocopy_plugin._invoke')
	def test_copy_and_move_commands_dispatch_the_action(self, invoke):
		CopyWithRobocopy(self.pane)()
		MoveWithRobocopy(self.pane)()
		self.assertEqual(
			['copy', 'move'], [call.args[0] for call in invoke.call_args_list]
		)

	def test_an_active_operation_is_rejected(self):
		self.assertTrue(_lock.acquire(blocking=False))
		try:
			with patch(
				'robocopy_plugin._queue_enabled', return_value=False, create=True
			), \
					patch('robocopy_plugin.fman.show_alert') as show_alert:
				CopyWithRobocopy(self.pane)()
		finally:
			_lock.release()
		show_alert.assert_called_once_with('A Robocopy operation is already active.')

	def test_queue_enabled_skips_busy_lock_and_defers_the_transfer_body(self):
		other = self.pane.window.get_panes.return_value[1]
		self.pane.get_path.return_value = 'file:///C:/source'
		self.pane.get_selected_files.return_value = ['file:///C:/source/file.txt']
		self.pane.window.get_panes.return_value = [self.pane, other]
		other.get_path.return_value = 'file:///C:/other'
		queued = []
		plan = Mock(jobs=())
		self.assertTrue(_lock.acquire(blocking=False))
		try:
			with patch(
				'robocopy_plugin._queue_enabled', return_value=True, create=True
			), \
					patch(
						'robocopy_plugin._run_queued',
						side_effect=lambda title, fn: queued.append((title, fn)),
						create=True
					), \
					patch('robocopy_plugin.fman.show_alert') as alert, \
					patch('robocopy_plugin.fman.show_input', return_value='C:\\dest'), \
					patch(
						'robocopy_plugin.fman.load_json', return_value={}
					) as load_json, \
					patch('robocopy_plugin.windows.executable',
						return_value='C:\\Windows\\robocopy.exe'), \
					patch(
						'robocopy_plugin.planner.prepare', return_value=plan
					) as prepare, \
					patch('robocopy_plugin.planner.probe') as probe, \
					patch('robocopy_plugin.fman.submit_task') as submit:
				_invoke('copy', CopyWithRobocopy(self.pane))

				alert.assert_not_called()
				self.assertEqual(1, len(queued))
				self.assertEqual('Copy with robocopy to C:\\dest', queued[0][0])
				load_json.assert_not_called()
				prepare.assert_not_called()
				probe.assert_not_called()
				submit.assert_not_called()

				queued[0][1]()

				load_json.assert_called_once_with('Robocopy', {})
				prepare.assert_called_once()
				probe.assert_called_once()
				submit.assert_called_once()
				self.pane.reload.assert_called_once_with()
				other.reload.assert_called_once_with()
		finally:
			_lock.release()

	def test_shipped_plugin_directory_is_discovered(self):
		with TemporaryDirectory() as root:
			shipped = Path(root) / 'Plugins'
			robocopy = shipped / 'Robocopy'
			robocopy.mkdir(parents=True)
			found = find_plugin_dirs(
				str(shipped), str(Path(root) / 'thirdparty'), str(Path(root) / 'user')
			)
			self.assertIn(str(robocopy), found)
