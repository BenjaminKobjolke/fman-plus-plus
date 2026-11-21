"""Settings and shared behavior for optional file-operation confirmations."""
from core.commands.util import NO_SELECTION
from core.settings import get_setting, save_setting, SETTINGS_FILE
from fman import ApplicationCommand, show_status_message

import fman

__all__ = [
	'ToggleCopyConfirmation', 'ToggleMoveConfirmation',
	'ToggleMoveToTrashConfirmation', 'ToggleDeletePermanentlyConfirmation',
]

CONFIRM_COPY = 'confirm_copy'
CONFIRM_MOVE = 'confirm_move'
CONFIRM_MOVE_TO_TRASH = 'confirm_move_to_trash'
CONFIRM_DELETE_PERMANENTLY = 'confirm_delete_permanently'


def is_confirm_enabled(key: str) -> bool:
	return get_setting(SETTINGS_FILE, key, True)


def skip_prompt_destination(command_cls, files, dest_dir, ui=fman, fs=fman.fs):
	if not files:
		ui.show_alert(NO_SELECTION)
		return
	if command_cls._is_into_itself(files, dest_dir, ui, fs):
		return
	return dest_dir, None


class _ToggleConfirmation(ApplicationCommand):
	_key = None
	_label = None

	def __call__(self):
		enabled = not is_confirm_enabled(self._key)
		save_setting(SETTINGS_FILE, self._key, enabled)
		state = 'on' if enabled else 'off'
		show_status_message(
			'%s confirmation: %s' % (self._label, state), timeout_secs=3
		)


class ToggleCopyConfirmation(_ToggleConfirmation):
	_key = CONFIRM_COPY
	_label = 'Copy'
	aliases = ('Toggle copy confirmation',)


class ToggleMoveConfirmation(_ToggleConfirmation):
	_key = CONFIRM_MOVE
	_label = 'Move'
	aliases = ('Toggle move confirmation',)


class ToggleMoveToTrashConfirmation(_ToggleConfirmation):
	_key = CONFIRM_MOVE_TO_TRASH
	_label = 'Move to trash'
	aliases = ('Toggle move to trash confirmation',)


class ToggleDeletePermanentlyConfirmation(_ToggleConfirmation):
	_key = CONFIRM_DELETE_PERMANENTLY
	_label = 'Delete permanently'
	aliases = ('Toggle delete permanently confirmation',)
