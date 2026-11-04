from unittest import TestCase
from unittest.mock import Mock, patch

from core.commands.taskbar import (
	PinFolderToTaskbar, TaskbarJumpListListener, UnpinFolderFromTaskbar,
)


class PinFolderToTaskbarTest(TestCase):
	def setUp(self):
		self.pane = Mock()
		self.pane.get_path.return_value = 'file:///C:/work/project'
		self.command = PinFolderToTaskbar(self.pane)
		path = patch(
			'core.commands.taskbar.as_human_readable',
			return_value=r'C:\work\project'
		)
		path.start()
		self.addCleanup(path.stop)

	def test_adds_current_folder_and_rebuilds_list(self):
		with patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch('core.commands.taskbar.get_pinned_folders', return_value=[]), \
				patch('core.commands.taskbar.save_pinned_folders') as save, \
				patch(
					'core.commands.taskbar.rebuild',
					return_value=[r'C:\work\project']
				) as rebuild, \
				patch('core.commands.taskbar.show_status_message') as show_status:
			self.command()
		save.assert_any_call([r'C:\work\project'])
		rebuild.assert_called_once_with([r'C:\work\project'])
		show_status.assert_called_once_with('Pinned to taskbar: project')

	def test_second_pin_reports_already_pinned_with_normalized_path(self):
		with patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch(
					'core.commands.taskbar.get_pinned_folders',
				return_value=[r'c:\WORK\project']
				), \
				patch('core.commands.taskbar.save_pinned_folders') as save, \
				patch('core.commands.taskbar.rebuild') as rebuild, \
				patch('core.commands.taskbar.show_status_message') as show_status:
			self.command()
		save.assert_not_called()
		rebuild.assert_not_called()
		show_status.assert_called_once_with('Already pinned to taskbar: project')

	def test_is_invisible_for_non_file_pane_and_other_platforms(self):
		with patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch(
					'core.commands.taskbar.is_file_url', return_value=False
				):
			self.assertFalse(self.command.is_visible())
		with patch('core.commands.taskbar.PLATFORM', 'Linux'):
			self.assertFalse(self.command.is_visible())


class UnpinFolderFromTaskbarTest(TestCase):
	def test_removes_selected_folder(self):
		command = UnpinFolderFromTaskbar(Mock())
		paths = [r'C:\One', r'C:\Two']
		with patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch('core.commands.taskbar.get_pinned_folders', return_value=paths), \
				patch(
					'core.commands.taskbar.show_quicksearch',
					return_value=('', r'C:\Two')
				) as quicksearch, \
				patch('core.commands.taskbar.save_pinned_folders') as save, \
				patch(
					'core.commands.taskbar.rebuild', return_value=[r'C:\One']
				) as rebuild, \
				patch(
					'core.commands.taskbar.show_status_message'
				) as show_status:
			command()
		get_items = quicksearch.call_args.args[0]
		items = list(get_items('two'))
		self.assertEqual([r'C:\Two'], [item.value for item in items])
		self.assertEqual([r'C:\One'], save.call_args.args[0])
		rebuild.assert_called_once_with([r'C:\One'])
		show_status.assert_called_once_with('Unpinned from taskbar: Two')

	def test_search_matches_every_term_as_case_insensitive_substrings(self):
		command = UnpinFolderFromTaskbar(Mock())
		with patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch(
					'core.commands.taskbar.get_pinned_folders',
					return_value=[r'C:\Release Builds\Nightly']
				), \
				patch(
					'core.commands.taskbar.show_quicksearch', return_value=None
				) as quicksearch:
			command()
		get_items = quicksearch.call_args.args[0]
		items = list(get_items('NIGHT release'))
		self.assertEqual(1, len(items))
		self.assertEqual(r'C:\Release Builds\Nightly', items[0].value)
		self.assertEqual([], list(get_items('release missing')))

	def test_is_visible_only_on_windows_with_saved_pins(self):
		command = UnpinFolderFromTaskbar(Mock())
		with patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch(
					'core.commands.taskbar.get_pinned_folders',
					return_value=['C:\\One']
				):
			self.assertTrue(command.is_visible())
		with patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch('core.commands.taskbar.get_pinned_folders', return_value=[]):
			self.assertFalse(command.is_visible())
		with patch('core.commands.taskbar.PLATFORM', 'Linux'), \
				patch(
					'core.commands.taskbar.get_pinned_folders',
					return_value=['C:\\One']
				):
			self.assertFalse(command.is_visible())


class TaskbarJumpListListenerTest(TestCase):
	def test_rebuilds_only_once_and_only_for_non_empty_list(self):
		from core.commands import taskbar
		listener = TaskbarJumpListListener(Mock())
		with patch.object(taskbar, '_LISTENER_REBUILT', False), \
				patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch(
					'core.commands.taskbar.get_pinned_folders',
					return_value=[r'C:\One']
				), \
				patch(
					'core.commands.taskbar.rebuild', return_value=[r'C:\One']
				) as rebuild, \
				patch('core.commands.taskbar.save_pinned_folders') as save:
			listener.on_path_changed()
			listener.on_path_changed()
			rebuild.assert_called_once_with([r'C:\One'])
			save.assert_not_called()

	def test_does_not_rebuild_empty_list(self):
		from core.commands import taskbar
		listener = TaskbarJumpListListener(Mock())
		with patch.object(taskbar, '_LISTENER_REBUILT', False), \
				patch('core.commands.taskbar.PLATFORM', 'Windows'), \
				patch('core.commands.taskbar.get_pinned_folders', return_value=[]), \
				patch('core.commands.taskbar.rebuild') as rebuild:
			listener.on_path_changed()
			rebuild.assert_not_called()
