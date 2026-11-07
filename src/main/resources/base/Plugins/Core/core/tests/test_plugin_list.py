from core.plugin_list import (
	PluginListEntry, PluginOs, PluginSource, entry_for_installed
)
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import json
import os


class PluginListEntryTest(TestCase):
	def test_json_round_trip(self):
		entry = PluginListEntry(
			'Example', PluginSource.GITHUB,
			'https://github.com/example/plugin', 'v1.2.3',
			PluginOs.LINUX, '2.1.4'
		)
		self.assertEqual(entry, PluginListEntry.from_json(entry.to_json()))
		self.assertEqual({
			'name': 'Example', 'source': 'github',
			'location': 'https://github.com/example/plugin', 'version': 'v1.2.3',
			'os': 'Linux', 'fman_version': '2.1.4'
		}, entry.to_json())

	def test_from_json_rejects_unknown_source(self):
		with self.assertRaises(ValueError):
			PluginListEntry.from_json(self._json(source='unknown'))

	def test_from_json_rejects_unknown_os(self):
		with self.assertRaises(ValueError):
			PluginListEntry.from_json(self._json(os='Plan9'))

	def test_entry_for_installed_reads_github_metadata(self):
		entry = self._installed_entry({'url': 'https://github.com/a/b', 'ref': 'v1'})
		self.assertEqual(PluginSource.GITHUB, entry.source)

	def test_entry_for_installed_converts_legacy_github_api_url(self):
		entry = self._installed_entry({
			'url': 'https://api.github.com/repos/a/b', 'ref': 'v1'
		})
		self.assertEqual('https://github.com/a/b', entry.location)
		self.assertEqual('v1', entry.version)

	def test_entry_for_installed_reads_catalog_metadata(self):
		entry = self._installed_entry({
			'source': 'catalog', 'location': 'Example', 'ref': '2.0'
		})
		self.assertEqual(PluginSource.CATALOG, entry.source)
		self.assertEqual('Example', entry.location)
		self.assertEqual('2.0', entry.version)

	def test_entry_for_installed_reads_explicit_github_metadata(self):
		entry = self._installed_entry({
			'source': 'github', 'location': 'https://github.com/a/b',
			'ref': 'v3'
		})
		self.assertEqual(PluginSource.GITHUB, entry.source)
		self.assertEqual('v3', entry.version)

	def test_entry_for_installed_returns_none_without_source_metadata(self):
		self.assertIsNone(self._installed_entry({'name': 'manually-copied'}))

	def _json(self, **changes):
		data = {
			'name': 'Example', 'source': 'github',
			'location': 'https://github.com/example/plugin', 'version': 'v1',
			'os': 'Linux', 'fman_version': '2.1.4'
		}
		data.update(changes)
		return data

	def _installed_entry(self, metadata):
		with TemporaryDirectory() as temp_dir:
			plugin_dir = os.path.join(temp_dir, 'ExamplePlugin')
			os.mkdir(plugin_dir)
			with open(os.path.join(plugin_dir, 'Plugin.json'), 'w') as f:
				json.dump(metadata, f)
			with patch('core.plugin_list.PLATFORM', 'Linux'), \
					patch('core.plugin_list.FMAN_VERSION', '2.1.4'):
				return entry_for_installed(plugin_dir)
