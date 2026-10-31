from core.commands.file_types import (
	ChooseFileTypeAction, OpenWithSystemDefault,
)
from core.commands.open_with import Configure
from core.file_type_actions import ActionKind, FileTypeAction
from unittest import TestCase
from unittest.mock import MagicMock, patch


class ConfigureFileTypeActionsTest(TestCase):
	def test_stop_option_only_exists_when_suffix_has_an_action(self):
		files = ['C:/files/readme.md']
		with patch('core.commands.open_with._load_apps', return_value={}):
			with patch(
				'core.commands.open_with.action_for_exact_suffix', return_value=None
			):
				options = list(Configure(files).get_options())
		self.assertFalse(any(
			option.startswith('Stop always opening') for option in options
		))
		with patch('core.commands.open_with._load_apps', return_value={}):
			with patch(
				'core.commands.open_with.action_for_exact_suffix',
				return_value=FileTypeAction(
					ActionKind.COMMAND_LINE,
					args=('Typora.exe', '{file}'), app='Typora'
				)
			):
				options = list(Configure(files).get_options())
		self.assertIn('Stop always opening .md files with Typora', options)


class ChooseFileTypeActionTest(TestCase):
	def setUp(self):
		self.save = patch('core.commands.file_types.set_action').start()
		self.addCleanup(patch.stopall)

	def test_picking_app_saves_app_arguments_and_name(self):
		with patch(
			'core.commands.file_types.app_args',
			return_value=('app.exe', '{file}')
		):
			ChooseFileTypeAction(
				'.md', {'Editor': 'app.exe'}, lambda: None
			).on_selected('Editor')
		self.save.assert_called_once_with('.md', FileTypeAction(
			ActionKind.COMMAND_LINE, args=('app.exe', '{file}'), app='Editor'
		))

	def test_fman_viewer_saves_command_action(self):
		ChooseFileTypeAction('.log', {}, lambda: None).on_selected('fman viewer')
		self.save.assert_called_once_with(
			'.log', FileTypeAction(ActionKind.COMMAND, command='view_file')
		)

	def test_command_line_parses_arguments_and_appends_file(self):
		with patch(
			'core.commands.file_types._show_app_open_dialog',
			return_value='csv.exe'
		), patch(
			'core.commands.file_types.show_prompt',
			return_value=('--sep ";"', True)
		), patch(
			'core.commands.file_types.parse_arguments',
			return_value=['--sep', ';']
		), patch(
			'core.commands.file_types.command_line_for',
			return_value=('csv.exe', '--sep', ';', '{file}')
		):
			ChooseFileTypeAction(
				'.csv', {}, lambda: None
			).on_selected('Command line...')
		self.save.assert_called_once_with('.csv', FileTypeAction(
			ActionKind.COMMAND_LINE, args=('csv.exe', '--sep', ';', '{file}')
		))

	def test_cancelling_program_or_arguments_saves_nothing(self):
		for dialog_value, prompt_value in (
			('', ('', False)), ('app.exe', ('', False))
		):
			with self.subTest(dialog_value=dialog_value):
				self.save.reset_mock()
				with patch(
					'core.commands.file_types._show_app_open_dialog',
					return_value=dialog_value
				), patch(
					'core.commands.file_types.show_prompt',
					return_value=prompt_value
				):
					ChooseFileTypeAction(
						'.csv', {}, lambda: None
					).on_selected('Command line...')
				self.save.assert_not_called()


class OpenWithSystemDefaultTest(TestCase):
	def test_bypasses_file_type_actions(self):
		pane = MagicMock()
		command = OpenWithSystemDefault(pane)
		command.get_chosen_files = MagicMock(return_value=['file:///a.md'])
		with patch('core.commands.file_types._open_files') as open_files:
			command()
		open_files.assert_called_once_with(
			['file:///a.md'], pane, use_file_type_actions=False
		)

	def test_no_chosen_file_shows_alert(self):
		command = OpenWithSystemDefault(MagicMock())
		command.get_chosen_files = MagicMock(return_value=[])
		with patch('core.commands.file_types.show_alert') as alert:
			command()
		alert.assert_called_once()

