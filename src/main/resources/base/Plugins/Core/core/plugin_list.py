"""Typed entries saved in the fman account's shared plugin list."""
from dataclasses import dataclass
from enum import Enum
from fman import FMAN_VERSION, PLATFORM

import json
import os


class PluginSource(Enum):
	CATALOG = 'catalog'
	FORGEJO = 'forgejo'
	GITHUB = 'github'
	GITLAB = 'gitlab'


class PluginOs(Enum):
	WINDOWS = 'Windows'
	MAC = 'Mac'
	LINUX = 'Linux'


@dataclass(frozen=True)
class PluginListEntry:
	name: str
	source: PluginSource
	location: str
	version: str
	os: PluginOs
	fman_version: str

	def __post_init__(self):
		if not isinstance(self.source, PluginSource):
			raise ValueError('Invalid plugin source: %r' % self.source)
		if not isinstance(self.os, PluginOs):
			raise ValueError('Invalid plugin operating system: %r' % self.os)
		for field in ('name', 'location', 'version', 'fman_version'):
			if not isinstance(getattr(self, field), str) or not getattr(self, field):
				raise ValueError('Plugin list %s must be a non-empty string' % field)

	def to_json(self):
		return {
			'name': self.name, 'source': self.source.value,
			'location': self.location, 'version': self.version,
			'os': self.os.value, 'fman_version': self.fman_version
		}

	@classmethod
	def from_json(cls, data):
		if not isinstance(data, dict):
			raise ValueError('Plugin list entry must be a JSON object')
		try:
			return cls(
				name=data['name'], source=PluginSource(data['source']),
				location=data['location'], version=data['version'],
				os=PluginOs(data['os']), fman_version=data['fman_version']
			)
		except KeyError as e:
			raise ValueError('Missing plugin list field: %s' % e.args[0]) from e
		except (TypeError, ValueError) as e:
			raise ValueError('Invalid plugin list entry: %s' % e) from e


def entry_for_installed(plugin_dir):
	"""Read sync metadata from an installed plugin, or return None if absent."""
	metadata_path = os.path.join(plugin_dir, 'Plugin.json')
	try:
		with open(metadata_path, encoding='utf-8') as f:
			metadata = json.load(f)
	except FileNotFoundError:
		return None

	source = metadata.get('source')
	if source is None and metadata.get('url'):
		# Existing GitHub installs store `url` and `ref` without a source field.
		source = PluginSource.GITHUB.value
	if source is None:
		return None
	location = metadata.get('location') or metadata.get('url')
	version = metadata.get('ref') or metadata.get('version')
	if not location or not version:
		return None
	if source == PluginSource.GITHUB.value and location.startswith(
			'https://api.github.com/repos/'):
		location = location.replace(
			'https://api.github.com/repos/', 'https://github.com/', 1
		)
	return PluginListEntry(
		name=os.path.basename(os.path.normpath(plugin_dir)),
		source=PluginSource(source), location=location, version=version,
		os=PluginOs(PLATFORM), fman_version=FMAN_VERSION
	)
