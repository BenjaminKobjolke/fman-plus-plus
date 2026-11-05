"""Commands for Windows Robocopy transfers."""

from threading import Lock
import os

import fman
from fman import DirectoryPaneCommand, PLATFORM
from fman.url import as_human_readable

from . import logs, planner, windows
from .settings import Settings
from .transfer import Transfer


_lock = Lock()
_SETTINGS_NAME = 'Robocopy'
_BUSY_MESSAGE = 'A Robocopy operation is already active.'
_NO_SELECTION_MESSAGE = 'Select one or more files or folders first.'


def _other_pane_path(command: DirectoryPaneCommand) -> str:
	panes = command.pane.window.get_panes()
	index = panes.index(command.pane)
	other = panes[(index + 1) % len(panes)]
	return as_human_readable(other.get_path()) if other is not command.pane else ''


def _prompt_text(action: str, selected: list[str]) -> str:
	verb = 'Move' if action == 'move' else 'Copy'
	if len(selected) == 1:
		name = os.path.basename(as_human_readable(selected[0]))
		return '%s "%s" with robocopy to' % (verb, name)
	return '%s %d files with robocopy to' % (verb, len(selected))


def _refresh(pane: DirectoryPaneCommand) -> None:
	for item in pane.pane.window.get_panes():
		item.reload()


def _invoke(action: str, command: DirectoryPaneCommand) -> None:
	if not _lock.acquire(blocking=False):
		fman.show_alert(_BUSY_MESSAGE)
		return
	try:
		selected = command.get_chosen_files()
		if not selected:
			fman.show_alert(_NO_SELECTION_MESSAGE)
			return
		pane = command.pane
		destination = fman.show_input(
			_prompt_text(action, selected), _other_pane_path(command), 0, None)
		if not destination:
			return
		settings = Settings.load(fman.load_json(_SETTINGS_NAME, {}))
		executable = windows.executable()
		log_path = (
			logs.choose_path(fman.DATA_DIRECTORY)
			if settings.log_enabled else None
		)
		plan = planner.prepare(pane.get_path(), selected, destination, executable,
			settings, move=action == 'move', log=log_path)
		planner.probe(executable, settings)
		title = 'Move with robocopy' if action == 'move' else 'Copy with robocopy'
		transfer = Transfer(title, plan, log_path, executable)
		fman.submit_task(transfer)
		_refresh(command)
	except (OSError, ValueError, RuntimeError) as error:
		fman.show_alert(str(error))
	finally:
		_lock.release()


class CopyWithRobocopy(DirectoryPaneCommand):
	aliases = ('Copy with robocopy',)

	def is_visible(self) -> bool:
		return PLATFORM == 'Windows'

	def __call__(self) -> None:
		_invoke('copy', self)


class MoveWithRobocopy(DirectoryPaneCommand):
	aliases = ('Move with robocopy',)

	def is_visible(self) -> bool:
		return PLATFORM == 'Windows'

	def __call__(self) -> None:
		_invoke('move', self)
