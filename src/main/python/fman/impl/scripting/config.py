"""Validated settings and shared constants for the scripting API."""

from dataclasses import dataclass
from ipaddress import ip_address, ip_network
import logging
from pathlib import Path
import secrets

_LOG = logging.getLogger(__name__)

STATE_PATH = '/v1/state'
COMMANDS_PATH = '/v1/commands'
COMMAND_PATH = '/v1/command'
AUTHORIZATION_HEADER = 'Authorization'
ORIGIN_HEADER = 'Origin'
SETTING_KEY = 'scripting_api'
ENABLED_KEY = 'enabled'
PORT_KEY = 'port'
ALLOWED_HOSTS_KEY = 'allowed_hosts'
COMMAND_ACCESS_KEY = 'command_access'
ALLOWED_COMMANDS_KEY = 'allowed_commands'
AUTOMATION_KEY = 'automation'
KEYS_PATH = '/v1/keys'
CLICK_PATH = '/v1/click'
SCREENSHOT_PATH = '/v1/screenshot'
DIALOG_PATH = '/v1/dialog'
FILES_PATH = '/v1/files'
STATUS_ON = 'Scripting API on: http://{address}:{port} (token in {token_path})'
STATUS_OFF = 'Scripting API off'
STATUS_START_FAILED = 'Scripting API could not start: {error}'

DEFAULT_PORT = 47447
DEFAULT_ALLOWED_COMMANDS = (
	'move_cursor_up',
	'move_cursor_down',
	'move_cursor_home',
	'move_cursor_end',
	'move_cursor_page_up',
	'move_cursor_page_down',
	'go_up',
	'go_back',
	'go_forward',
	'open_directory',
	'reload',
	'select_all',
	'deselect',
	'invert_selection',
	'toggle_selection',
	'switch_panes',
	'toggle_hidden_files',
	'sort_by_column',
	'copy_paths_to_clipboard',
	'copy_file_path',
	'copy_file_name',
	'center_window',
	'minimize',
)


@dataclass(frozen=True)
class ScriptingApiConfig:
	enabled: bool
	automation: bool
	port: int
	allowed_networks: tuple
	allow_all_commands: bool
	allowed_commands: frozenset

	@classmethod
	def from_settings(cls, local_settings):
		settings = local_settings.get(SETTING_KEY, {})
		if not isinstance(settings, dict):
			_LOG.warning(
				'Ignoring invalid %s setting; expected an object.', SETTING_KEY)
			settings = {}

		enabled = settings.get(ENABLED_KEY, False)
		if not isinstance(enabled, bool):
			_LOG.warning('Ignoring invalid scripting API enabled setting.')
			enabled = False

		automation = settings.get(AUTOMATION_KEY, False)
		if not isinstance(automation, bool):
			_LOG.warning('Ignoring invalid scripting API automation setting.')
			automation = False

		port = settings.get(PORT_KEY, DEFAULT_PORT)
		if (
			not isinstance(port, int) or isinstance(port, bool)
			or not 1 <= port <= 65535
		):
			_LOG.warning(
				'Ignoring invalid scripting API port; using %s.', DEFAULT_PORT)
			port = DEFAULT_PORT

		allowed_networks = []
		allowed_hosts = settings.get(ALLOWED_HOSTS_KEY, [])
		if not isinstance(allowed_hosts, list):
			_LOG.warning(
				'Ignoring invalid scripting API allowed_hosts; expected a list.')
			allowed_hosts = []
		for host in allowed_hosts:
			if not isinstance(host, str):
				_LOG.warning('Ignoring invalid scripting API host %r.', host)
				continue
			try:
				allowed_networks.append(ip_network(host, strict=False))
			except ValueError:
				_LOG.warning('Ignoring invalid scripting API host %r.', host)

		command_access = settings.get(COMMAND_ACCESS_KEY, 'allowlist')
		if command_access not in ('allowlist', 'all'):
			_LOG.warning(
				'Ignoring invalid scripting API command_access; using allowlist.')
			command_access = 'allowlist'

		allowed_commands = settings.get(
			ALLOWED_COMMANDS_KEY, list(DEFAULT_ALLOWED_COMMANDS))
		if not isinstance(allowed_commands, list) or any(
			not isinstance(command, str) for command in allowed_commands
		):
			_LOG.warning(
				'Ignoring invalid scripting API allowed_commands; using defaults.')
			allowed_commands = DEFAULT_ALLOWED_COMMANDS

		return cls(
			enabled,
			automation,
			port,
			tuple(allowed_networks),
			command_access == 'all',
			frozenset(allowed_commands),
		)

	@property
	def bind_address(self):
		return '0.0.0.0' if self.allowed_networks else '127.0.0.1'

	def is_command_allowed(self, name):
		return self.allow_all_commands or name in self.allowed_commands

	def is_client_allowed(self, address):
		try:
			client = ip_address(address)
		except ValueError:
			return False
		return client.is_loopback or any(
			client.version == network.version and client in network
			for network in self.allowed_networks
		)


def load_or_create_token(path):
	path = Path(path)
	try:
		return path.read_text(encoding='utf-8').strip()
	except FileNotFoundError:
		path.parent.mkdir(parents=True, exist_ok=True)
		token = secrets.token_urlsafe(32)
		path.write_text(token, encoding='utf-8')
		return token
