from core import plugin_installation
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import os
import json


class PluginInstallationTest(TestCase):
	def test_install_zip_copies_root_contents_when_there_is_no_single_top_folder(self):
		with TemporaryDirectory() as directory:
			zip_bytes = b'zip contents'
			with patch.object(
					plugin_installation, '_THIRDPARTY_PLUGINS_DIR', directory
			), \
					patch.object(plugin_installation, 'exists', return_value=False), \
					patch.object(
						plugin_installation, 'iterdir',
						return_value=['Plugin.json', 'core.py']
					), \
					patch.object(plugin_installation, 'is_dir', return_value=False), \
					patch.object(plugin_installation, 'copy') as copy:
				plugin_dir = plugin_installation.install_zip('Example', zip_bytes)
				self.assertEqual(os.path.join(directory, 'Example'), plugin_dir)
				copy.assert_called_once()
				self.assertTrue(copy.call_args.args[0].startswith('zip://'))
				self.assertEqual(
					plugin_installation.as_url(plugin_dir), copy.call_args.args[1]
				)

	def test_install_zip_copies_the_only_top_folder(self):
		with TemporaryDirectory() as directory, \
				patch.object(
					plugin_installation, '_THIRDPARTY_PLUGINS_DIR', directory
				), \
				patch.object(plugin_installation, 'exists', return_value=False), \
				patch.object(
					plugin_installation, 'iterdir', return_value=['Example-1.0']
				), \
				patch.object(plugin_installation, 'is_dir', return_value=True), \
				patch.object(plugin_installation, 'copy') as copy:
			plugin_installation.install_zip('Example', b'zip contents')
			self.assertTrue(copy.call_args.args[0].endswith('/Example-1.0'))

	def test_record_and_load_installation_metadata(self):
		with TemporaryDirectory() as plugin_dir:
			plugin_installation.record_installation(
				plugin_dir, 'https://github.com/example/plugin', 'v1.0'
			)
			with open(os.path.join(plugin_dir, 'Plugin.json'), encoding='utf-8') as f:
				self.assertEqual({
					'url': 'https://github.com/example/plugin', 'ref': 'v1.0'
				}, json.load(f))

	def test_record_catalog_installation_metadata(self):
		with TemporaryDirectory() as plugin_dir:
			plugin_installation.record_installation(
				plugin_dir, 'Example', '2.0', source='catalog'
			)
			with open(os.path.join(plugin_dir, 'Plugin.json'), encoding='utf-8') as f:
				self.assertEqual({
					'source': 'catalog', 'location': 'Example', 'ref': '2.0'
				}, json.load(f))

	def test_load_installed_plugin_preserves_order(self):
		window = type('Window', (), {'get_panes': lambda self: []})()
		with patch.object(
				plugin_installation, '_get_plugins', return_value=['one', 'two']
		), \
				patch.object(
					plugin_installation, 'load_plugin', return_value=True
			) as load, \
				patch.object(plugin_installation, 'unload_plugin') as unload:
			self.assertTrue(plugin_installation.load_installed_plugin('one', window))
		unload.assert_called_once_with('two')
		self.assertEqual(
			[('one',), ('two',)], [call.args for call in load.call_args_list]
		)

	def test_remove_plugin_dir_unloads_and_deletes(self):
		with patch.object(plugin_installation, 'unload_plugin') as unload, \
				patch.object(plugin_installation, 'delete') as delete, \
				patch.object(plugin_installation, 'as_url', return_value='file:///plugin'):
			plugin_installation.remove_plugin_dir('/plugin')
		unload.assert_called_once_with('/plugin')
		delete.assert_called_once_with('file:///plugin')
