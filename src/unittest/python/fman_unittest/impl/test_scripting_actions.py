from unittest import TestCase
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QApplication

from fman.impl.scripting.actions import InvalidPane, ScriptingActions, UnknownCommand


_APP = QApplication.instance() or QApplication([])


class ScriptingActionsTest(TestCase):
	def setUp(self):
		self.plugin_support = MagicMock()
		self.main_window = MagicMock()
		self.pane = MagicMock()
		self.other_pane = MagicMock()
		self.plugin_support.get_panes.return_value = [self.pane, self.other_pane]
		self.plugin_support.get_active_pane.return_value = self.other_pane
		self.actions = ScriptingActions(self.plugin_support, self.main_window)

	def test_get_state_lists_active_pane_first(self):
		self.other_pane.get_path.return_value = 'file:///right'
		self.other_pane.get_file_under_cursor.return_value = None
		self.other_pane.get_selected_files.return_value = []
		self.pane.get_path.return_value = 'file:///left'
		self.pane.get_file_under_cursor.return_value = 'file:///left/a.txt'
		self.pane.get_selected_files.return_value = ['file:///left/a.txt']

		self.assertEqual({
			'active_pane': 0,
			'panes': [
				{'path': 'file:///right', 'cursor': None, 'selection': []},
				{
					'path': 'file:///left',
					'cursor': 'file:///left/a.txt',
					'selection': ['file:///left/a.txt'],
				},
			],
		}, self.actions.get_state())

	def test_get_commands_reports_available_and_allowed_names(self):
		self.pane.get_commands.return_value = {'open_directory', 'reload'}
		self.other_pane.get_commands.return_value = {'go_up'}
		self.plugin_support.get_application_commands.return_value = {'quit'}
		config = MagicMock()
		config.allow_all_commands = False
		config.allowed_commands = {'open_directory'}

		self.assertEqual({
			'pane': ['go_up', 'open_directory', 'reload'],
			'application': ['quit'],
			'allowed': ['open_directory'],
		}, self.actions.get_commands(config))

	def test_get_commands_uses_null_for_all_allowed(self):
		self.pane.get_commands.return_value = set()
		self.other_pane.get_commands.return_value = set()
		self.plugin_support.get_application_commands.return_value = set()
		config = MagicMock()
		config.allow_all_commands = True

		self.assertIsNone(self.actions.get_commands(config)['allowed'])

	def test_run_command_dispatches_to_selected_pane(self):
		self.pane.get_commands.return_value = {'open_directory'}
		self.other_pane.get_commands.return_value = {'open_directory'}
		args = {'url': 'file:///tmp'}

		self.actions.run_command('open_directory', args, 0)

		self.other_pane.run_command.assert_called_once_with('open_directory', args)

	def test_run_command_dispatches_application_command_without_checking_pane(self):
		self.pane.get_commands.return_value = set()
		self.other_pane.get_commands.return_value = set()
		self.plugin_support.get_application_commands.return_value = {'minimize'}

		self.actions.run_command('minimize', {}, 3)

		self.plugin_support.run_application_command.assert_called_once_with(
			'minimize', {})
		self.plugin_support.get_panes.assert_not_called()

	def test_run_command_dispatches_application_command_without_panes(self):
		self.plugin_support.get_panes.return_value = []
		self.plugin_support.get_application_commands.return_value = {'minimize'}

		self.actions.run_command('minimize', {}, 0)

		self.plugin_support.run_application_command.assert_called_once_with(
			'minimize', {})

	def test_run_command_rejects_unknown_commands_and_invalid_panes(self):
		self.pane.get_commands.return_value = set()
		self.other_pane.get_commands.return_value = set()
		self.plugin_support.get_application_commands.return_value = set()
		with self.assertRaises(UnknownCommand):
			self.actions.run_command('missing', {}, None)
		with self.assertRaises(InvalidPane):
			self.actions.run_command('open_directory', {}, 3)
