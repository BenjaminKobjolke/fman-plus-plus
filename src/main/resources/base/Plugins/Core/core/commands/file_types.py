"""Commands and screens for configuring persistent file type actions."""
from core.commands.editor import _show_app_open_dialog
from core.commands.app_arguments import ask_arguments
from core.commands.opening import _open_files
from core.commands.util import is_file_url, NO_SELECTION
from core.file_type_actions import (
	ActionKind, FileTypeAction, app_args, command_line_for, set_action,
)
from core.quicksearch_screen import QuicksearchScreen
from fman import DirectoryPaneCommand, show_alert, \
	show_status_message


__all__ = ['OpenWithSystemDefault']


class OpenWithSystemDefault(DirectoryPaneCommand):
	aliases = ('Open with system default',)

	def __call__(self):
		urls = self.get_chosen_files()
		if not urls:
			show_alert(NO_SELECTION)
			return
		_open_files(urls, self.pane, use_file_type_actions=False)

	def is_visible(self):
		return is_file_url(self.pane.get_path()) and bool(
			self.pane.get_file_under_cursor()
		)


class ChooseFileTypeAction(QuicksearchScreen):
	_VIEWER = 'fman viewer'
	_EDITOR = 'fman editor (F4)'
	_COMMAND_LINE = 'Command line...'
	_COMMANDS = {
		_VIEWER: 'view_file',
		_EDITOR: 'open_with_editor',
	}

	def __init__(self, suffix, app_paths, on_back):
		super().__init__()
		self._suffix = suffix
		self._app_paths = app_paths
		self._on_back = on_back

	def get_options(self):
		yield from sorted(self._app_paths)
		yield self._VIEWER
		yield self._EDITOR
		yield self._COMMAND_LINE

	def on_selected(self, option):
		if option in self._app_paths:
			action = FileTypeAction(
				ActionKind.COMMAND_LINE,
				args=app_args(self._app_paths[option]), app=option
			)
		elif option in self._COMMANDS:
			action = FileTypeAction(
				ActionKind.COMMAND, command=self._COMMANDS[option]
			)
		elif option == self._COMMAND_LINE:
			action = self._choose_command_line()
			if action is None:
				return
		else:
			return
		set_action(self._suffix, action)
		show_status_message(
			'Enter now opens %s files with %s.' % (
				self._suffix, action.label()
			), timeout_secs=3
		)

	def _choose_command_line(self):
		program = _show_app_open_dialog('Pick a program')
		if not program:
			return None
		arguments = ask_arguments('{file}')
		if arguments is None:
			return None
		return FileTypeAction(
			ActionKind.COMMAND_LINE,
			args=command_line_for(program, arguments)
		)

	def on_cancelled(self):
		self._on_back()
