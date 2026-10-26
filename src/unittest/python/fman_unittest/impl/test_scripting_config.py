from ipaddress import ip_address
from tempfile import TemporaryDirectory
from unittest import TestCase

from fman.impl.scripting.config import (
	DEFAULT_ALLOWED_COMMANDS,
	DEFAULT_PORT,
	ScriptingApiConfig,
	load_or_create_token,
)


class ScriptingApiConfigTest(TestCase):
	def test_defaults_when_setting_is_missing(self):
		config = ScriptingApiConfig.from_settings(_Settings({}))

		self.assertFalse(config.enabled)
		self.assertEqual('127.0.0.1', config.bind_address)
		self.assertFalse(config.allow_all_commands)
		self.assertEqual(frozenset(DEFAULT_ALLOWED_COMMANDS), config.allowed_commands)

	def test_custom_allowed_commands_replace_the_defaults(self):
		config = ScriptingApiConfig.from_settings(_Settings({
			'scripting_api': {'allowed_commands': ['open_directory']},
		}))

		self.assertEqual(frozenset({'open_directory'}), config.allowed_commands)
		self.assertTrue(config.is_command_allowed('open_directory'))
		self.assertFalse(config.is_command_allowed('delete_permanently'))

	def test_command_access_all_and_invalid_value(self):
		all_config = ScriptingApiConfig.from_settings(_Settings({
			'scripting_api': {'command_access': 'all'},
		}))
		invalid_config = ScriptingApiConfig.from_settings(_Settings({
			'scripting_api': {'command_access': 'sometimes'},
		}))

		self.assertTrue(all_config.allow_all_commands)
		self.assertTrue(all_config.is_command_allowed('anything'))
		self.assertFalse(invalid_config.allow_all_commands)
		self.assertFalse(invalid_config.is_command_allowed('anything'))

	def test_allowed_hosts_support_ip_and_cidr_and_skip_invalid_entries(self):
		config = ScriptingApiConfig.from_settings(_Settings({
			'scripting_api': {
				'allowed_hosts': ['192.168.1.9', '10.2.0.0/16', 'not-an-ip'],
			},
		}))

		self.assertEqual('0.0.0.0', config.bind_address)
		self.assertTrue(config.is_client_allowed(ip_address('127.0.0.1')))
		self.assertTrue(config.is_client_allowed(ip_address('192.168.1.9')))
		self.assertTrue(config.is_client_allowed(ip_address('10.2.3.4')))
		self.assertFalse(config.is_client_allowed(ip_address('10.3.3.4')))

	def test_bad_port_type_uses_default(self):
		config = ScriptingApiConfig.from_settings(_Settings({
			'scripting_api': {'port': '47448'},
		}))

		self.assertEqual(DEFAULT_PORT, config.port)

	def test_toggle_command_is_not_in_default_allowlist(self):
		self.assertNotIn('toggle_scripting_api', DEFAULT_ALLOWED_COMMANDS)

	def test_token_is_created_once_and_reused(self):
		with TemporaryDirectory() as directory:
			path = f'{directory}/ScriptingApiToken.txt'

			first_token = load_or_create_token(path)
			second_token = load_or_create_token(path)

			self.assertTrue(first_token)
			self.assertEqual(first_token, second_token)


class _Settings:
	def __init__(self, values):
		self._values = values

	def get(self, key, default):
		return self._values.get(key, default)
