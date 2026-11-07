"""Installing, removing, listing and reloading fman plugins.

Installing unloads every plugin after the new one in the load order and loads
them again, so the new plugin lands in the right place. Pane paths are saved
across that (`PreservePanePaths`) because a filesystem that is reloaded takes
the location displaying it down with it.
"""
from core.github import find_repos, GitHubRepo
from core.plugin_info_dialog import show_plugin_info
from core.fman_api import FmanApiClient, FmanApiError
from core.plugin_catalog import CatalogPlugin, search as search_catalog
from core.plugin_list import entry_for_installed
from core.plugin_sync import record_install, record_remove
from core.quicksearch_matchers import contains_chars
from core.plugin_installation import (
	PreservePanePaths, _get_plugins, _get_thirdparty_plugins,
	_get_user_plugins, install_zip, load_installed_plugin,
	record_installation, remove_plugin_dir
)
from fman import ApplicationCommand, DirectoryPaneCommand, \
	QuicksearchItem, clear_status_message, load_plugin, show_alert, \
	show_quicksearch, show_status_message, unload_plugin
from fman.url import as_url
from urllib.error import URLError

import json
import os
import os.path

__all__ = [
	'InstallPlugin', 'ListPlugins', 'PreservePanePaths', 'ReloadPlugins',
	'RemovePlugin', 'StatusMessage'
]

_NO_DESCRIPTION = 'No description available.'

def _matches_query(name, query):
	# The highlight for `name`, or None if it does not match. An empty query
	# matches everything - and contains_chars answers it with an empty
	# highlight, which is falsy, hence the explicit test.
	match = contains_chars(name.lower(), query.lower())
	if match or not query:
		return match
	return None

class InstallPlugin(ApplicationCommand):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._plugin_repos = None
		self._catalog_client = None
		self._catalog_results = {}
	def __call__(self, github_repo=None):
		if github_repo:
			with StatusMessage('Fetching GitHub repo %s...' % github_repo):
				repo = GitHubRepo.fetch(github_repo)
		else:
			if self._plugin_repos is None:
				with StatusMessage('Fetching available plugins...'):
					try:
						self._plugin_repos = \
							find_repos(topics=['fman', 'plugin'])
					except URLError as e:
						show_alert(
							'Could not fetch available plugins: %s.' % e.reason
						)
						return
			repo = self._pick_repo()
		if repo:
			with StatusMessage('Downloading %s...' % repo.name):
				try:
					ref = repo.get_latest_release()
				except LookupError:
					if isinstance(repo, CatalogPlugin):
						show_alert('Plugin %r has no released versions.' % repo.name)
						return
					ref = repo.get_latest_commit()
				zipball_contents = repo.download_zipball(ref)
			plugin_dir = install_zip(repo.name, zipball_contents)
			# Save some data in case we want to update the plugin later:
			if isinstance(repo, CatalogPlugin):
				record_installation(
					plugin_dir, repo.location, ref, source=repo.source
				)
			else:
				record_installation(plugin_dir, repo.url, ref)
			success = load_installed_plugin(plugin_dir, self.window)
			if success:
				entry = entry_for_installed(plugin_dir)
				if entry is not None:
					record_install(entry)
				show_alert('Plugin %r was successfully installed.' % repo.name)
	def _pick_repo(self):
		query = ''
		while True:
			result = show_quicksearch(self._get_matching_repos, query=query)
			if not result:
				return None
			query, repo = result[0], result[1]
			with StatusMessage('Fetching description of %s...' % repo.name):
				description = repo.fetch_description()
			if show_plugin_info(repo.name,
					description or _fallback_description(repo)):
				return repo
	def _get_matching_repos(self, query):
		installed_plugins = set(
			os.path.basename(plugin_dir)
			for plugin_dir in _get_thirdparty_plugins()
		)
		github_names = set()
		for repo in self._plugin_repos:
			if repo.name in installed_plugins:
				continue
			match = _matches_query(repo.name, query)
			if match is not None:
				github_names.add(repo.name)
				hint = '%d ★' % repo.num_stars if repo.num_stars else ''
				yield QuicksearchItem(
					repo, repo.name, match, hint=hint,
					description=repo.description
				)
		for plugin in self._get_catalog_plugins(query):
			if plugin.name in installed_plugins or plugin.name in github_names:
				continue
			match = _matches_query(plugin.name, query)
			if match is not None:
				yield QuicksearchItem(
					plugin, plugin.name, match, hint='fman catalog',
					description=plugin.description
				)
	def _get_catalog_plugins(self, query):
		if query not in self._catalog_results:
			if self._catalog_client is None:
				self._catalog_client = FmanApiClient()
			try:
				self._catalog_results[query] = search_catalog(
					self._catalog_client, query
				)
			except FmanApiError:
				self._catalog_results[query] = ()
		return self._catalog_results[query]

def _fallback_description(repo):
	parts = ['# ' + repo.name]
	if repo.description:
		parts.extend(('', repo.description))
	parts.extend(('', '*' + _NO_DESCRIPTION + '*'))
	return '\n'.join(parts)

class RemovePlugin(ApplicationCommand):

	aliases = ('Remove plugin',)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._installed_plugins = None
	def __call__(self):
		self._installed_plugins = _get_thirdparty_plugins()
		if not self._installed_plugins:
			show_alert("You don't seem to have any plugins installed.")
		else:
			result = show_quicksearch(self._get_matching_plugins)
			if result:
				plugin_dir = result[1]
				if plugin_dir:
					plugin_name = os.path.basename(plugin_dir)
					remove_plugin_dir(plugin_dir)
					record_remove(plugin_name)
					show_alert(
						'Plugin %r was successfully removed.'
						% plugin_name
					)
	def _get_matching_plugins(self, query):
		for plugin_dir in self._installed_plugins:
			plugin_name = os.path.basename(plugin_dir)
			match = _matches_query(plugin_name, query)
			if match is not None:
				yield QuicksearchItem(plugin_dir, plugin_name, highlight=match)

class ReloadPlugins(ApplicationCommand):
	def __call__(self):
		plugins = _get_plugins()
		with PreservePanePaths(self.window):
			for plugin in reversed(plugins):
				try:
					unload_plugin(plugin)
				except ValueError:
					pass
			for plugin in plugins:
				load_plugin(plugin)
		num_plugins = len(plugins)
		plural = 's' if num_plugins > 1 else ''
		show_status_message(
			'Reloaded %d plugin%s.' % (num_plugins, plural), timeout_secs=2
		)

class ListPlugins(DirectoryPaneCommand):
	def __call__(self):
		result = show_quicksearch(self._get_matching_plugins)
		if result:
			plugin_dir = result[1]
			if plugin_dir:
				self.pane.set_path(as_url(plugin_dir), onerror=None)
	def _get_matching_plugins(self, query):
		result = []
		for plugin_dir in _get_thirdparty_plugins():
			plugin_name = os.path.basename(plugin_dir)
			match = _matches_query(plugin_name, query)
			if match is not None:
				plugin_json = os.path.join(plugin_dir, 'Plugin.json')
				try:
					with open(plugin_json, 'r') as f:
						ref = json.load(f).get('ref', '')
				except OSError:
					ref = ''
				is_sha = len(ref) == 40
				if is_sha:
					ref = ref[:8]
				result.append(QuicksearchItem(
					plugin_dir, plugin_name, highlight=match, hint=ref
				))
		for plugin_dir in _get_user_plugins():
			plugin_name = os.path.basename(plugin_dir)
			match = _matches_query(plugin_name, query)
			if match is not None:
				result.append(
					QuicksearchItem(plugin_dir, plugin_name, highlight=match)
				)
		return sorted(result, key=lambda qsi: qsi.title)

class StatusMessage:
	def __init__(self, message):
		self._message = message
	def __enter__(self):
		show_status_message(self._message)
	def __exit__(self, *_):
		clear_status_message()
