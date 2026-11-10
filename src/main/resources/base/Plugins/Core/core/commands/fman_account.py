"""Commands for signing in and synchronizing the account's plugin list."""
from core.fman_account import (
	clear_token, is_signed_in, sign_in, signed_in_client,
)
from core.fman_api import FmanApiAuthError, FmanApiClient, FmanApiError
from core.github import GitHubRepo
from core.plugin_hosts import repo_for_location
from core.plugin_installation import (
	_get_thirdparty_plugins, install_zip, load_installed_plugin,
	record_installation, remove_plugin_dir,
)
from core.plugin_list import PluginOs, PluginSource, entry_for_installed
from core.plugin_sync import SyncState, compute_sync
from core.plugin_sync_dialog import PluginSyncDialog
from core.settings_sync_runner import sync_settings
from fman import (
	ApplicationCommand, DirectoryPaneListener, NO, OK, PLATFORM,
	YES, run_application_command, show_alert, show_status_message,
)
from os.path import basename
from urllib.error import URLError


__all__ = [
	'PluginSyncOnStartup', 'SignInToFmanAccount', 'SignOutOfFmanAccount',
	'ShowFmanAccount', 'SyncPlugins', 'SyncSettings',
]

_STARTUP_SYNC_STARTED = False
_REMOVE_MESSAGE = (
	'The following plugins were removed from your fman account on another '
	'computer. Remove them here too?\n\n%s'
)
_NETWORK_ERROR = 'Could not sync plugins: %s'
_SETTINGS_NETWORK_ERROR = 'Could not sync settings: %s'


class SignInToFmanAccount(ApplicationCommand):
	aliases = ('Sign in to fman account',)

	def is_visible(self):
		return not is_signed_in()

	def __call__(self):
		try:
			result = sign_in(FmanApiClient())
		except (FmanApiError, TimeoutError, OSError) as error:
			show_alert('Could not sign in to fman account: %s' % error)
			return
		message = 'Signed in to fman account'
		if result.email:
			message += ': ' + result.email
		show_alert(message)
		run_application_command('sync_settings')


class SignOutOfFmanAccount(ApplicationCommand):
	aliases = ('Sign out of fman account',)

	def is_visible(self):
		return is_signed_in()

	def __call__(self):
		clear_token()
		show_status_message('Signed out of fman account')


class ShowFmanAccount(ApplicationCommand):
	aliases = ('fman account',)

	def is_visible(self):
		return is_signed_in()

	def __call__(self):
		try:
			client = signed_in_client()
			if client is None:
				show_status_message('Signed out of fman account')
				return
			account = client.me()
		except FmanApiError as error:
			show_status_message('Could not load fman account: %s' % error)
			return

		parts = [part for part in (account.name, account.email) if part]
		message = 'Signed in to fman account'
		if parts:
			message += ' as ' + ' '.join(parts)
		if show_alert(message, OK | YES, OK, button_texts={YES: 'Sign out'}) & YES:
			run_application_command('sign_out_of_fman_account')


class SyncSettings(ApplicationCommand):
	aliases = ('Sync settings',)

	def __call__(self, silent=False):
		try:
			client = signed_in_client()
		except FmanApiError as error:
			show_status_message(_SETTINGS_NETWORK_ERROR % error)
			return
		if client is None:
			if not silent:
				show_status_message('Signed out of fman account')
			return
		sync_settings(client)


class SyncPlugins(ApplicationCommand):
	aliases = ('Sync plugins',)

	def __call__(self, silent=False, include_ignored=False):
		try:
			client = signed_in_client()
		except FmanApiError as error:
			show_status_message(_NETWORK_ERROR % error)
			return
		if client is None:
			if not silent:
				show_status_message('Signed out of fman account')
			return
		state = SyncState.load()
		try:
			server_entries = client.get_plugin_list()
			server = {entry.name: entry for entry in server_entries}
			installed_dirs = _get_thirdparty_plugins()
			installed = {
				basename(plugin_dir): _entry_for_installed(plugin_dir)
				for plugin_dir in installed_dirs
			}
			plan = compute_sync(
				server, installed, state, PluginOs(PLATFORM),
				include_ignored=include_ignored
			)
			for entry in plan.to_upload:
				client.put_plugin(entry)
				server[entry.name] = entry
			for name in plan.to_delete:
				client.delete_plugin(name)
				server.pop(name, None)
		except FmanApiAuthError:
			clear_token()
			show_status_message('Signed out of fman account')
			return
		except FmanApiError as error:
			show_status_message(_NETWORK_ERROR % error)
			return

		installed_now, selected_names = self._install_selected(client, plan)
		removed_now = self._remove_confirmed(plan.to_remove, installed_dirs)
		for entry in plan.to_install:
			if selected_names is not None and entry.name not in selected_names:
				state.ignored[entry.name] = entry.version
			elif entry.name in installed_now:
				state.ignored.pop(entry.name, None)
		# Keep local names marked as synced when a removal was declined so the
		# next sync asks again instead of uploading the plugin back to the list.
		state.synced_names = set(server) | (set(installed) - removed_now)
		state.save()

	def _install_selected(self, client, plan):
		if not plan.to_install:
			return set(), set()
		dialog = PluginSyncDialog(plan.to_install, PluginOs(PLATFORM))
		if not dialog.exec_():
			return set(), None
		installed = set()
		selected = dialog.selected_entries()
		for entry in selected:
			try:
				if entry.source == PluginSource.CATALOG:
					repo_url = entry.location
					archive = client.download_release(entry.name, entry.version)
					metadata_source = 'catalog'
				elif entry.source in (PluginSource.GITLAB, PluginSource.FORGEJO):
					repo = repo_for_location(entry.source, entry.location)
					repo_url = entry.location
					archive = repo.download_zipball(entry.version)
					metadata_source = entry.source.value
				else:
					repo = GitHubRepo.fetch(entry.location)
					repo_url = repo.url
					archive = repo.download_zipball(entry.version)
					metadata_source = None
				plugin_dir = install_zip(entry.name, archive)
				record_installation(
					plugin_dir, repo_url, entry.version, source=metadata_source
				)
				if load_installed_plugin(plugin_dir, self.window):
					installed.add(entry.name)
			except (FmanApiError, OSError, URLError, ValueError) as error:
				show_status_message(_NETWORK_ERROR % error)
		return installed, {entry.name for entry in selected}

	def _remove_confirmed(self, names, installed_dirs):
		if not names:
			return set()
		if not (show_alert(
			_REMOVE_MESSAGE % '\n'.join(names), YES | NO, YES
		) & YES):
			return set()
		paths_by_name = {basename(path): path for path in installed_dirs}
		removed = set()
		for name in names:
			path = paths_by_name.get(name)
			if path:
				remove_plugin_dir(path)
				removed.add(name)
		return removed

class PluginSyncOnStartup(DirectoryPaneListener):
	def on_path_changed(self):
		global _STARTUP_SYNC_STARTED
		if _STARTUP_SYNC_STARTED:
			return
		_STARTUP_SYNC_STARTED = True
		run_application_command('sync_plugins', {'silent': True})
		run_application_command('sync_settings', {'silent': True})


def _entry_for_installed(plugin_dir):
	try:
		return entry_for_installed(plugin_dir)
	except (OSError, TypeError, ValueError):
		return None
