"""Connect per-file settings sync decisions to the account API and local files."""
from core.fman_account import signed_in_client
from core.fman_api import FmanApiClient, FmanApiConflictError, FmanApiError
from core.plugin_list import PluginOs
from core.quicksearch_screen import QuicksearchScreen
from core.settings_sync import (
	SettingsSyncState, SyncedEntry, SyncedSettingsKind, SyncAction, combine,
	content_hash,
	decide,
)
from core.user_bindings import save_user_bindings, user_bindings_path
from fman import PLATFORM, show_status_message
from typing import Iterable
from enum import Enum
import json


_NETWORK_ERROR = 'Could not sync settings: %s'
class ConflictChoice(Enum):
	KEEP_LOCAL = 'keep_local'
	USE_ACCOUNT = 'use_account'
	COMBINE = 'combine'


_CHOICE_LABELS = {
	'Keep this computer\'s': ConflictChoice.KEEP_LOCAL,
	'Use the account\'s': ConflictChoice.USE_ACCOUNT,
	'Combine both': ConflictChoice.COMBINE,
}


class SettingsConflictPicker(QuicksearchScreen):
	def __init__(self, kind: SyncedSettingsKind) -> None:
		self.kind = kind
		self.choice: ConflictChoice | None = None

	def choose(self) -> ConflictChoice | None:
		self.show()
		return self.choice

	def get_title(self) -> str:
		return 'Settings changed: %s' % self.kind.value.replace('_', ' ')

	def get_options(self) -> list[str]:
		return list(_CHOICE_LABELS)

	def on_selected(self, option: str) -> None:
		self.choice = _CHOICE_LABELS[option]


def ask_conflict(kind: SyncedSettingsKind) -> ConflictChoice | None:
	"""Return the user's conflict choice, or None when they press Escape."""
	return SettingsConflictPicker(kind).choose()


def sync_settings(
	client: FmanApiClient | None = None,
	kinds: Iterable[SyncedSettingsKind] = tuple(SyncedSettingsKind),
) -> None:
	"""Sync selected settings files and save successful revisions once at the end."""
	if client is None:
		try:
			client = signed_in_client()
		except FmanApiError as error:
			show_status_message(_NETWORK_ERROR % error)
			return
	if client is None:
		return

	state = SettingsSyncState.load()
	changed = False
	for kind in kinds:
		local = _read_local(kind)
		entry = state.entries.get(kind)
		try:
			remote = client.get_settings(PluginOs(PLATFORM).value, kind.value)
			action = decide(local, remote, entry)
			changed |= _apply_action(client, kind, local, remote, entry, action, state)
			if action is SyncAction.NOTHING and remote is not None:
				changed |= _record(state, kind, remote.revision, remote.content)
		except FmanApiError as error:
			show_status_message(_NETWORK_ERROR % error)
	if changed:
		state.save()


def record_settings_change(file_name: str) -> None:
	"""Upload one edited user settings file when the account is available."""
	kind = SyncedSettingsKind.for_file(file_name)
	if kind is None:
		return
	try:
		client = signed_in_client()
		if client is None:
			return
		state = SettingsSyncState.load()
		local = _read_local(kind)
		entry = state.entries.get(kind)
		remote = client.get_settings(PluginOs(PLATFORM).value, kind.value)
		action = decide(local, remote, entry)
		if action is SyncAction.NOTHING and remote is not None:
			changed = _record(state, kind, remote.revision, remote.content)
		else:
			changed = _apply_action(client, kind, local, remote, entry, action, state)
		if changed:
			state.save()
	except FmanApiError as error:
		show_status_message(_NETWORK_ERROR % error)


def _apply_action(client, kind, local, remote, entry, action, state) -> bool:
	if action is SyncAction.NOTHING:
		return False
	if action is SyncAction.PULL:
		if remote is None:
			return False
		_save_local(kind, remote.content)
		return _record(state, kind, remote.revision, remote.content)
	if action is SyncAction.PUSH:
		return _push(client, kind, local, entry.revision if entry else None, state)
	return _ask_and_apply(client, kind, local, remote, state)


def _ask_and_apply(client, kind, local, remote, state) -> bool:
	choice = ask_conflict(kind)
	if choice is None:
		return False
	if choice == ConflictChoice.USE_ACCOUNT:
		content = remote.content if remote is not None else kind.empty_value
		_save_local(kind, content)
		if remote is None:
			state.entries.pop(kind, None)
			return True
		return _record(state, kind, remote.revision, content)

	remote_content = remote.content if remote is not None else kind.empty_value
	local_content = local
	if choice == ConflictChoice.COMBINE:
		local_content = combine(kind, local, remote_content)
		_save_local(kind, local_content)

	try:
		saved = client.put_settings(
			PluginOs(PLATFORM).value, kind.value,
			remote.revision if remote is not None else None, local_content
		)
	except FmanApiConflictError as conflict:
		return _retry_conflict(client, kind, local_content, conflict, state)
	return _record(state, kind, saved.revision, saved.content)


def _retry_conflict(client, kind, local, conflict, state) -> bool:
	choice = ask_conflict(kind)
	if choice is None:
		return False
	current = conflict.current
	if choice == ConflictChoice.USE_ACCOUNT:
		content = current.content if current is not None else kind.empty_value
		_save_local(kind, content)
		if current is None:
			state.entries.pop(kind, None)
			return True
		return _record(state, kind, current.revision, content)
	if choice == ConflictChoice.COMBINE:
		local = combine(
			kind, local, current.content if current is not None else kind.empty_value
		)
		_save_local(kind, local)
	try:
		saved = client.put_settings(
			PluginOs(PLATFORM).value, kind.value,
			current.revision if current is not None else None, local
		)
	except FmanApiConflictError as second_conflict:
		show_status_message(_NETWORK_ERROR % second_conflict)
		return False
	return _record(state, kind, saved.revision, saved.content)


def _push(client, kind, content, base_revision, state) -> bool:
	try:
		saved = client.put_settings(
			PluginOs(PLATFORM).value, kind.value, base_revision, content
		)
	except FmanApiConflictError as conflict:
		return _retry_conflict(client, kind, content, conflict, state)
	return _record(state, kind, saved.revision, saved.content)


def _read_local(kind: SyncedSettingsKind) -> list | dict:
	try:
		with open(
			user_bindings_path(kind.file_name), encoding='utf-8'
		) as settings_file:
			content = json.load(settings_file)
	except (OSError, UnicodeError, ValueError):
		return kind.empty_value
	expected_type = type(kind.empty_value)
	return content if isinstance(content, expected_type) else kind.empty_value


def _save_local(kind: SyncedSettingsKind, content: list | dict) -> None:
	save_user_bindings(kind.file_name, content)


def _record(state, kind, revision, content) -> bool:
	entry = SyncedEntry(revision, content_hash(content))
	if state.entries.get(kind) == entry:
		return False
	state.entries[kind] = entry
	return True
