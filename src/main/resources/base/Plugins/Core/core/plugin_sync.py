"""Compare the shared plugin list with this computer's installed plugins."""
from core.plugin_list import PluginListEntry, PluginOs
from core.fman_account import signed_in_client
from core.fman_api import FmanApiError
from dataclasses import dataclass, field
from fman import DATA_DIRECTORY
from fman import show_status_message
from os.path import join
from typing import Mapping

import json
import os


_STATE_FILENAME = join('Local', 'Plugin Sync.json')


@dataclass(frozen=True)
class SyncPlan:
	to_install: tuple[PluginListEntry, ...] = ()
	to_remove: tuple[str, ...] = ()
	to_upload: tuple[PluginListEntry, ...] = ()
	to_delete: tuple[str, ...] = ()


@dataclass
class SyncState:
	"""Per-computer names and remote versions the user chose to ignore."""

	synced_names: set[str] = field(default_factory=set)
	ignored: dict[str, str] = field(default_factory=dict)

	@classmethod
	def load(cls) -> 'SyncState':
		path = join(DATA_DIRECTORY, _STATE_FILENAME)
		try:
			with open(path, encoding='utf-8') as state_file:
				data = json.load(state_file)
			return cls._from_json(data)
		except (OSError, UnicodeError, ValueError, TypeError):
			return cls()

	@classmethod
	def _from_json(cls, data: object) -> 'SyncState':
		if not isinstance(data, dict):
			raise ValueError('Plugin sync state must be an object')
		synced_names = data.get('synced_names', [])
		ignored = data.get('ignored', {})
		if not isinstance(synced_names, list) or not all(
			isinstance(name, str) and name for name in synced_names
		):
			raise ValueError('Plugin sync state synced_names must be a list of names')
		if not isinstance(ignored, dict) or not all(
			isinstance(name, str) and name and isinstance(version, str) and version
			for name, version in ignored.items()
		):
			raise ValueError('Plugin sync state ignored must map names to versions')
		return cls(set(synced_names), dict(ignored))

	def to_json(self) -> dict[str, object]:
		return {
			'synced_names': sorted(self.synced_names),
			'ignored': dict(sorted(self.ignored.items()))
		}

	def save(self) -> None:
		path = join(DATA_DIRECTORY, _STATE_FILENAME)
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, 'w', encoding='utf-8') as state_file:
			json.dump(self.to_json(), state_file, indent=2, sort_keys=True)


def compute_sync(
	server: Mapping[str, PluginListEntry] | None,
	installed: Mapping[str, PluginListEntry | None],
	state: SyncState,
	this_os: PluginOs,
	include_ignored: bool = False
) -> SyncPlan:
	"""Return the sync actions without changing local, remote or persisted state.

	Pass ``None`` for ``server`` when offline. Previously synced local removals
	remain in ``to_delete`` so a caller can send those deletes on the next sync.
	"""
	if not isinstance(this_os, PluginOs):
		raise ValueError('Invalid plugin operating system: %r' % this_os)

	server_online = server is not None
	server = server or {}
	server_names = set(server)
	installed_names = set(installed)
	previously_synced = state.synced_names

	to_install = []
	for name, entry in server.items():
		if name in installed_names:
			continue
		if not include_ignored and state.ignored.get(name) == entry.version:
			continue
		to_install.append(entry)

	to_remove = []
	to_upload = []
	for name, entry in installed.items():
		if server_online and name in previously_synced and name not in server_names:
			to_remove.append(name)
		elif (
			server_online and name not in server_names
			and name not in previously_synced and entry is not None
			and entry.os == this_os
		):
			to_upload.append(entry)

	to_delete = sorted(
		name for name in previously_synced
		if name not in installed_names and (not server_online or name in server_names)
	)
	return SyncPlan(
		to_install=tuple(sorted(to_install, key=lambda entry: entry.name)),
		to_remove=tuple(sorted(to_remove)),
		to_upload=tuple(sorted(to_upload, key=lambda entry: entry.name)),
		to_delete=tuple(to_delete)
	)


def record_install(entry: PluginListEntry) -> None:
	"""Upload a successfully installed plugin when the account is available."""
	try:
		client = signed_in_client()
		if client is None:
			return
		client.put_plugin(entry)
	except FmanApiError as error:
		show_status_message('Could not sync plugins: %s' % error)
		return
	state = SyncState.load()
	state.synced_names.add(entry.name)
	state.ignored.pop(entry.name, None)
	state.save()


def record_remove(name: str) -> None:
	"""Delete a removed plugin from the account when signed in."""
	try:
		client = signed_in_client()
		if client is None:
			return
		client.delete_plugin(name)
	except FmanApiError as error:
		show_status_message('Could not sync plugins: %s' % error)
		return
	state = SyncState.load()
	state.synced_names.discard(name)
	state.ignored.pop(name, None)
	state.save()
