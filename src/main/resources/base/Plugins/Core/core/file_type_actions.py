"""Persistent file type actions, with the OS association as the fallback."""
from core.os_ import get_popen_kwargs_for_opening
from fman import load_json, save_json, show_status_message
from fman.url import as_url
from dataclasses import dataclass
from enum import Enum
from os.path import basename
from shutil import which
from subprocess import Popen
from typing import Collection, Protocol, Sequence


FILE_TYPE_ACTIONS_JSON = 'File Type Actions.json'
FILE_PLACEHOLDER = '{file}'


class ActionKind(Enum):
	COMMAND = 'command'
	COMMAND_LINE = 'command_line'


@dataclass(frozen=True)
class FileTypeAction:
	kind: ActionKind
	command: str = ''
	args: tuple[str, ...] = ()
	app: str = ''

	def label(self) -> str:
		if self.app:
			return self.app
		if self.kind is ActionKind.COMMAND:
			return {
				'view_file': 'fman viewer',
				'open_with_editor': 'fman editor (F4)',
			}.get(self.command, self.command)
		return basename(self.args[0]) if self.args else ''

	def to_json(self) -> dict[str, object]:
		if self.kind is ActionKind.COMMAND:
			return {'command': self.command}
		value = {'command_line': list(self.args)}
		if self.app:
			value['app'] = self.app
		return value

	@classmethod
	def from_json(cls, value: object) -> 'FileTypeAction | None':
		if not isinstance(value, dict):
			return None
		command = value.get('command')
		if isinstance(command, str) and command:
			return cls(ActionKind.COMMAND, command=command)
		args = value.get('command_line')
		app = value.get('app', '')
		if isinstance(args, list) and args and all(
			isinstance(argument, str) for argument in args
		) and isinstance(app, str):
			return cls(ActionKind.COMMAND_LINE, args=tuple(args), app=app)
		return None


def suffix_of(file_name: str) -> str:
	index = file_name.rfind('.')
	return file_name[index:] if index >= 0 else ''


def action_for(file_name: str) -> FileTypeAction | None:
	name = file_name.lower()
	actions = _load_actions()
	for suffix in sorted(actions, key=len, reverse=True):
		if (isinstance(suffix, str) and suffix.startswith('.')
				and name.endswith(suffix.lower())):
			action = FileTypeAction.from_json(actions[suffix])
			if action is not None:
				return action
	return None


def action_for_exact_suffix(suffix: str) -> FileTypeAction | None:
	"""Return an action stored for this suffix, without suffix fallback."""
	value = _load_actions().get(suffix.lower())
	return FileTypeAction.from_json(value)


def set_action(suffix: str, action: FileTypeAction) -> None:
	actions = _load_actions()
	actions[suffix.lower()] = action.to_json()
	_save_actions()


def remove_action(suffix: str) -> None:
	actions = _load_actions()
	actions.pop(suffix.lower(), None)
	_save_actions()


def command_line_for(program: str, arguments: Sequence[str]) -> tuple[str, ...]:
	"""Build a command line; Mac .app bundles need their inner binary."""
	# Shortcut: custom command lines run the picked path directly on Mac, so
	# a .app bundle needs its inner binary; upgrade when a Mac user asks.
	args = (program, *arguments)
	if not any(FILE_PLACEHOLDER in argument for argument in args):
		args += (FILE_PLACEHOLDER,)
	return tuple(args)


def app_args(app_path: str) -> tuple[str, ...]:
	kwargs = get_popen_kwargs_for_opening([FILE_PLACEHOLDER], with_=app_path)
	return tuple(kwargs['args'])


def rename_app(old_name: str, new_name: str, new_path: str) -> None:
	actions = _load_actions()
	for suffix, value in actions.items():
		action = FileTypeAction.from_json(value)
		if action and action.kind is ActionKind.COMMAND_LINE and action.app == old_name:
			actions[suffix] = FileTypeAction(
				ActionKind.COMMAND_LINE, args=app_args(new_path), app=new_name
			).to_json()
	_save_actions()


class _FileTypeActionPane(Protocol):
	def get_commands(self) -> Collection[str]: ...
	def place_cursor_at(self, url: str) -> None: ...
	def run_command(self, name: str) -> None: ...


def run_file_type_actions(
	paths: Sequence[str], pane: _FileTypeActionPane
) -> list[str]:
	remaining = []
	for path in paths:
		action = action_for(basename(path))
		if action is None:
			remaining.append(path)
			continue
		suffix = suffix_of(basename(path))
		try:
			if action.kind is ActionKind.COMMAND_LINE:
				program = action.args[0]
				if which(program) is None:
					raise OSError('program not found: %s' % program)
				Popen([
					argument.replace(FILE_PLACEHOLDER, path)
					for argument in action.args
				])
			else:
				if action.command not in pane.get_commands():
					raise ValueError('unknown fman command: %s' % action.command)
				pane.place_cursor_at(as_url(path))
				pane.run_command(action.command)
			continue
		except (OSError, ValueError) as error:
			show_status_message(
				'Could not apply the %s action: %s. '
				'Opening with the system default.' % (
					suffix, error
				), timeout_secs=5
			)
			remaining.append(path)
	return remaining


def _load_actions() -> dict[str, object]:
	value = load_json(FILE_TYPE_ACTIONS_JSON, {})
	return value if isinstance(value, dict) else {}


def _save_actions() -> None:
	save_json(FILE_TYPE_ACTIONS_JSON)
