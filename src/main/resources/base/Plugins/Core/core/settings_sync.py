"""Pure settings sync decisions and per-computer sync history."""
from core.command_keywords import COMMAND_KEYWORDS_FILE
from core.command_titles import COMMAND_TITLES_FILE
from core.fman_api import SyncedSettingsDocument
from core.key_bindings import KEY_BINDINGS_FILE, VIEWER_KEY_BINDINGS_FILE
from dataclasses import dataclass, field
from enum import Enum
from fman import DATA_DIRECTORY
from os.path import dirname, join
import hashlib
import json
import os


_STATE_FILENAME = join('Local', 'Settings Sync.json')


class SyncedSettingsKind(Enum):
	KEY_BINDINGS = 'key_bindings'
	VIEWER_KEY_BINDINGS = 'viewer_key_bindings'
	COMMAND_TITLES = 'command_titles'
	COMMAND_KEYWORDS = 'command_keywords'

	@property
	def file_name(self) -> str:
		match self:
			case SyncedSettingsKind.KEY_BINDINGS:
				return KEY_BINDINGS_FILE
			case SyncedSettingsKind.VIEWER_KEY_BINDINGS:
				return VIEWER_KEY_BINDINGS_FILE
			case SyncedSettingsKind.COMMAND_TITLES:
				return COMMAND_TITLES_FILE
			case SyncedSettingsKind.COMMAND_KEYWORDS:
				return COMMAND_KEYWORDS_FILE

	@property
	def empty_value(self) -> list | dict:
		match self:
			case (
				SyncedSettingsKind.KEY_BINDINGS
				| SyncedSettingsKind.VIEWER_KEY_BINDINGS
			):
				return []
			case (
				SyncedSettingsKind.COMMAND_TITLES
				| SyncedSettingsKind.COMMAND_KEYWORDS
			):
				return {}

	@classmethod
	def for_file(cls, name: str) -> 'SyncedSettingsKind | None':
		return next((kind for kind in cls if kind.file_name == name), None)


@dataclass(frozen=True)
class SyncedEntry:
	"""The last remote version and content recorded on this computer."""

	revision: int
	content_hash: str


@dataclass
class SettingsSyncState:
	"""Per-computer sync history, stored independently from user settings."""

	entries: dict[SyncedSettingsKind, SyncedEntry] = field(default_factory=dict)

	@classmethod
	def load(cls) -> 'SettingsSyncState':
		path = join(DATA_DIRECTORY, _STATE_FILENAME)
		try:
			with open(path, encoding='utf-8') as state_file:
				return cls._from_json(json.load(state_file))
		except (OSError, UnicodeError, ValueError, TypeError):
			return cls()

	@classmethod
	def _from_json(cls, data: object) -> 'SettingsSyncState':
		if not isinstance(data, dict):
			raise ValueError('Settings sync state must be an object')
		entries = {}
		for kind_name, entry_data in data.items():
			if not isinstance(kind_name, str) or not isinstance(entry_data, dict):
				raise ValueError('Settings sync state entries must be objects')
			try:
				kind = SyncedSettingsKind(kind_name)
			except ValueError as error:
				raise ValueError('Unknown settings sync kind') from error
			revision = entry_data.get('revision')
			value_hash = entry_data.get('content_hash')
			if (
				isinstance(revision, bool) or not isinstance(revision, int)
				or revision < 1 or not isinstance(value_hash, str)
				or len(value_hash) != 64
			):
				raise ValueError('Invalid settings sync entry')
			try:
				int(value_hash, 16)
			except ValueError as error:
				raise ValueError('Invalid settings sync content hash') from error
			entries[kind] = SyncedEntry(revision, value_hash)
		return cls(entries)

	def to_json(self) -> dict[str, dict[str, int | str]]:
		return {
			kind.value: {
				'revision': entry.revision,
				'content_hash': entry.content_hash,
			}
			for kind, entry in sorted(
				self.entries.items(), key=lambda item: item[0].value
			)
		}

	def save(self) -> None:
		path = join(DATA_DIRECTORY, _STATE_FILENAME)
		os.makedirs(dirname(path), exist_ok=True)
		with open(path, 'w', encoding='utf-8') as state_file:
			json.dump(self.to_json(), state_file, indent=2, sort_keys=True)


class SyncAction(Enum):
	NOTHING = 'nothing'
	PULL = 'pull'
	PUSH = 'push'
	ASK = 'ask'


def content_hash(content: list | dict) -> str:
	"""Hash JSON content consistently regardless of object key order or spacing."""
	canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
	return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def decide(
	local: list | dict,
	remote: SyncedSettingsDocument | None,
	entry: SyncedEntry | None,
) -> SyncAction:
	"""Choose a sync action without mutating either copy or the saved state."""
	local_hash = content_hash(local)
	if remote is None:
		return SyncAction.NOTHING if not local else SyncAction.PUSH

	remote_hash = content_hash(remote.content)
	if entry is None:
		if local_hash == remote_hash:
			return SyncAction.NOTHING
		if not local:
			return SyncAction.PULL
		return SyncAction.ASK

	local_changed = local_hash != entry.content_hash
	remote_changed = remote_hash != entry.content_hash
	if local_changed and remote_changed:
		return SyncAction.NOTHING if local_hash == remote_hash else SyncAction.ASK
	if local_changed:
		return SyncAction.PUSH
	if remote_changed:
		return SyncAction.PULL
	return SyncAction.NOTHING


def combine(
	kind: SyncedSettingsKind, local: list | dict, remote: list | dict
) -> list | dict:
	"""Merge settings with local values taking precedence over remote values."""
	if kind in (
		SyncedSettingsKind.KEY_BINDINGS,
		SyncedSettingsKind.VIEWER_KEY_BINDINGS,
	):
		combined = list(local)
		local_keys = {
			_normalized_keys(item) for item in local if isinstance(item, dict)
		}
		for item in remote:
			keys = _normalized_keys(item) if isinstance(item, dict) else None
			if keys not in local_keys:
				combined.append(item)
				local_keys.add(keys)
		return combined
	return {**remote, **local}


def _normalized_keys(item: dict) -> tuple | None:
	keys = item.get('keys')
	return tuple(keys) if isinstance(keys, list) else keys
