from core.file_type_actions import (
	ActionKind, FileTypeAction, action_for, command_line_for,
	remove_action, rename_app, run_file_type_actions, set_action, suffix_of,
)
from fman.url import as_url
from unittest import TestCase
from unittest.mock import MagicMock, patch


class FileTypeActionsTest(TestCase):
	def setUp(self):
		self.data = {}
		self.load = patch(
			'core.file_type_actions.load_json',
			side_effect=lambda name, default=None: self.data
		).start()
		self.addCleanup(patch.stopall)
		self.save = patch('core.file_type_actions.save_json').start()

	def test_action_for_uses_longest_case_insensitive_suffix(self):
		self.data.update({
			'.gz': {'command': 'gzip'},
			'.tar.gz': {'command': 'archive'},
			'.md': {'command': 'view_file'},
		})
		self.assertEqual('archive', action_for('backup.tar.gz').command)
		self.assertEqual('view_file', action_for('NOTES.MD').command)
		self.assertIsNone(action_for('README'))

	def test_action_for_ignores_malformed_entries(self):
		self.data.update({
			'.str': 'command', '.empty': {'command_line': []},
			'.number': {'command_line': ['app', 3]},
			'no-dot': {'command': 'view_file'},
		})
		for name in ('x.str', 'x.empty', 'x.number', 'x.no-dot'):
			with self.subTest(name=name):
				self.assertIsNone(action_for(name))

	def test_command_line_for_appends_placeholder_when_missing(self):
		self.assertEqual(
			('program', '--new', '{file}'),
			command_line_for('program', ['--new'])
		)

	def test_command_line_for_preserves_placeholder_position(self):
		self.assertEqual(
			('program', '{file}', '--new'),
			command_line_for('program', ['{file}', '--new'])
		)

	def test_run_command_line_action_substitutes_file(self):
		path = r'C:\files\a.md'
		self.data['.md'] = {'command_line': ['editor', '--file={file}']}
		pane = MagicMock(spec=['get_commands', 'place_cursor_at', 'run_command'])
		with patch('core.file_type_actions.which', return_value='editor'), \
				patch('core.file_type_actions.Popen') as popen:
			remaining = run_file_type_actions([path], pane)
		self.assertEqual([], remaining)
		popen.assert_called_once_with(['editor', '--file=' + path])

	def test_missing_program_falls_back_and_shows_status(self):
		path = r'C:\files\a.md'
		self.data['.md'] = {'command_line': ['missing', '{file}']}
		pane = MagicMock(spec=['get_commands', 'place_cursor_at', 'run_command'])
		with patch('core.file_type_actions.which', return_value=None), \
				patch('core.file_type_actions.show_status_message') as status:
			self.assertEqual([path], run_file_type_actions([path], pane))
			status.assert_called_once()
			self.assertIn('.md', status.call_args.args[0])

	def test_popen_error_falls_back(self):
		path = 'C:/files/a.md'
		self.data['.md'] = {'command_line': ['editor', '{file}']}
		pane = MagicMock(spec=['get_commands', 'place_cursor_at', 'run_command'])
		with patch('core.file_type_actions.which', return_value='editor'), \
				patch('core.file_type_actions.Popen', side_effect=OSError('bad')):
			self.assertEqual([path], run_file_type_actions([path], pane))

	def test_command_action_places_cursor_and_runs_command(self):
		path = 'C:/files/a.log'
		self.data['.log'] = {'command': 'view_file'}
		pane = MagicMock(spec=['get_commands', 'place_cursor_at', 'run_command'])
		pane.get_commands.return_value = ['view_file']
		self.assertEqual([], run_file_type_actions([path], pane))
		pane.place_cursor_at.assert_called_once_with(as_url(path))
		pane.run_command.assert_called_once_with('view_file')

	def test_unknown_command_falls_back(self):
		path = 'C:/files/a.log'
		self.data['.log'] = {'command': 'missing'}
		pane = MagicMock(spec=['get_commands', 'place_cursor_at', 'run_command'])
		pane.get_commands.return_value = []
		self.assertEqual([path], run_file_type_actions([path], pane))

	def test_unconfigured_paths_are_returned_and_mixed_actions_run(self):
		configured, ordinary = 'C:/a.log', 'C:/b.unknown'
		self.data['.log'] = {'command': 'view_file'}
		pane = MagicMock(spec=['get_commands', 'place_cursor_at', 'run_command'])
		pane.get_commands.return_value = ['view_file']
		self.assertEqual(
			[ordinary], run_file_type_actions([configured, ordinary], pane)
		)

	def test_set_and_remove_action_normalize_suffix_and_save(self):
		action = FileTypeAction(ActionKind.COMMAND, command='view_file')
		set_action('.MD', action)
		self.assertEqual({'command': 'view_file'}, self.data['.md'])
		self.save.assert_called_with('File Type Actions.json')
		remove_action('.MD')
		self.assertNotIn('.md', self.data)

	def test_rename_app_rewrites_only_matching_app_entries(self):
		self.data.update({
			'.md': {'command_line': ['old.exe', '{file}'], 'app': 'Old'},
			'.txt': {'command_line': ['other.exe', '{file}'], 'app': 'Other'},
		})
		with patch(
				'core.file_type_actions.app_args',
				return_value=('new.exe', '{file}')
		):
			rename_app('Old', 'New', 'new.exe')
		self.assertEqual(
			{'command_line': ['new.exe', '{file}'], 'app': 'New'}, self.data['.md']
		)
		self.assertEqual('Other', self.data['.txt']['app'])

	def test_suffix_of_uses_last_dot(self):
		self.assertEqual('.gz', suffix_of('a.tar.gz'))
		self.assertEqual('', suffix_of('README'))

