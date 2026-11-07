"""Shared filesystem operations for installing, loading and removing plugins."""
from contextlib import contextmanager
from fman import DATA_DIRECTORY, load_plugin, unload_plugin
from fman.fs import copy, delete, exists, is_dir, iterdir
from fman.url import as_url, join
from core.util import listdir_absolute
from tempfile import TemporaryDirectory

import json
import os


_THIRDPARTY_PLUGINS_DIR = os.path.join(DATA_DIRECTORY, 'Plugins', 'Third-party')


def install_zip(name: str, zip_bytes: bytes) -> str:
	"""Install an archive with one wrapper folder or files at its root."""
	os.makedirs(_THIRDPARTY_PLUGINS_DIR, exist_ok=True)
	dest_dir = os.path.join(_THIRDPARTY_PLUGINS_DIR, name)
	dest_dir_url = as_url(dest_dir)
	if exists(dest_dir_url):
		raise ValueError('Plugin %s seems to already be installed.' % name)
	# Use fman's ZIP filesystem so executable bits survive extraction.
	with TemporaryDirectory() as tmp_dir:
		zip_path = os.path.join(tmp_dir, 'plugin.zip')
		with open(zip_path, 'wb') as f:
			f.write(zip_bytes)
		zip_url = as_url(zip_path, 'zip://')
		entries = list(iterdir(zip_url))
		if len(entries) == 1 and is_dir(join(zip_url, entries[0])):
			source_url = join(zip_url, entries[0])
		else:
			source_url = zip_url
		copy(source_url, dest_dir_url)
	return dest_dir


def record_installation(plugin_dir: str, repo_url: str, ref: str,
		source: str | None = None) -> None:
	plugin_json = os.path.join(plugin_dir, 'Plugin.json')
	if os.path.exists(plugin_json):
		with open(plugin_json, 'r', encoding='utf-8') as f:
			data = json.load(f)
	else:
		data = {}
	if source is None:
		# Keep the existing metadata shape for GitHub installs.
		data['url'] = repo_url
	else:
		data['source'] = source
		data['location'] = repo_url
	data['ref'] = ref
	with open(plugin_json, 'w', encoding='utf-8') as f:
		json.dump(data, f)


def load_installed_plugin(plugin_dir: str, window) -> bool:
	"""Load in the configured order while preserving visible pane paths."""
	plugins = _get_plugins()
	plugin_index = plugins.index(plugin_dir)
	to_unload = plugins[plugin_index + 1:]
	with PreservePanePaths(window):
		for plugin in reversed(to_unload):
			try:
				unload_plugin(plugin)
			except ValueError:
				pass
		result = load_plugin(plugin_dir)
		for plugin in to_unload:
			load_plugin(plugin)
	return result


def remove_plugin_dir(plugin_dir: str) -> None:
	try:
		unload_plugin(plugin_dir)
	except ValueError:
		pass
	delete(as_url(plugin_dir))


@contextmanager
def PreservePanePaths(window):
	paths = [pane.get_path() for pane in window.get_panes()]
	try:
		yield
	finally:
		for pane, path in zip(window.get_panes(), paths):
			pane.set_path(path)


def _get_plugins():
	return _get_thirdparty_plugins() + _get_user_plugins()


def _get_thirdparty_plugins():
	return _list_plugins(_THIRDPARTY_PLUGINS_DIR)


def _get_user_plugins():
	result = []
	settings_plugin = ''
	user_plugins_dir = os.path.join(DATA_DIRECTORY, 'Plugins', 'User')
	for plugin_dir in _list_plugins(user_plugins_dir):
		if os.path.basename(plugin_dir) == 'Settings':
			settings_plugin = plugin_dir
		else:
			result.append(plugin_dir)
	if settings_plugin:
		result.append(settings_plugin)
	return result


def _list_plugins(dir_path):
	try:
		return list(filter(os.path.isdir, listdir_absolute(dir_path)))
	except FileNotFoundError:
		return []
