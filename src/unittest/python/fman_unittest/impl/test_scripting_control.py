from fman.impl.scripting.config import SETTING_KEY
from fman.impl.scripting.control import ScriptingApiControl
from fman.impl.scripting.server import ScriptingServer
from fman.impl.util.settings import Settings
from tempfile import TemporaryDirectory
from os.path import join
from unittest import TestCase
from unittest.mock import MagicMock


class ScriptingApiControlTest(TestCase):
	def setUp(self):
		self.temp_dir = TemporaryDirectory()
		self.addCleanup(self.temp_dir.cleanup)
		self.settings_path = join(self.temp_dir.name, 'Settings.json')
		self.settings = Settings(self.settings_path)
		self.token_path = join(self.temp_dir.name, 'ScriptingApiToken.txt')
		self.servers = []
		self.start_error = None

		def server_factory(config, token):
			server = MagicMock(spec=ScriptingServer)
			server.config = config
			server.token = token
			if self.start_error:
				server.start.side_effect = self.start_error
			self.servers.append(server)
			return server

		self.control = ScriptingApiControl(
			self.settings, self.token_path, server_factory)

	def _settings(self):
		return self.settings.get(SETTING_KEY, {})

	def test_toggle_starts_and_persists_enabled_then_stops(self):
		self.settings[SETTING_KEY] = {'port': 12345, 'allowed_hosts': []}
		self.assertEqual(
			'Scripting API on: http://127.0.0.1:12345 (token in ' +
			self.token_path + ')', self.control.toggle())
		self.assertTrue(self.control.is_running)
		self.servers[0].start.assert_called_once_with()
		self.assertTrue(self._settings()['enabled'])

		self.assertEqual('Scripting API off', self.control.toggle())
		self.servers[0].stop.assert_called_once_with()
		self.assertFalse(self.control.is_running)
		self.assertFalse(self._settings()['enabled'])

	def test_start_failure_leaves_enabled_false_and_returns_error(self):
		self.settings[SETTING_KEY] = {'enabled': False}
		self.start_error = OSError('port is in use')
		self.assertEqual(
			'Scripting API could not start: port is in use', self.control.toggle())
		self.assertFalse(self._settings()['enabled'])
		self.assertFalse(self.control.is_running)

	def test_start_reloads_config_and_builds_a_new_server_each_time(self):
		self.settings[SETTING_KEY] = {'enabled': False, 'port': 1234}
		self.control.start()
		self.control.stop()
		self.settings[SETTING_KEY] = {'enabled': False, 'port': 2345}
		self.control.start()
		self.assertEqual([1234, 2345], [s.config.port for s in self.servers])
		self.assertEqual(2, len(self.servers))

	def test_token_is_created_and_other_settings_survive_toggles(self):
		other_settings = {
			'port': 1234, 'allowed_hosts': ['192.168.1.0/24'],
			'allowed_commands': ['go_up'], 'enabled': False,
		}
		self.settings[SETTING_KEY] = other_settings.copy()
		self.control.toggle()
		self.assertTrue(__import__('os').path.isfile(self.token_path))
		self.assertEqual(other_settings | {'enabled': True}, self._settings())
		self.control.toggle()
		self.assertEqual(other_settings, self._settings())

	def test_stop_when_stopped_does_nothing(self):
		self.control.stop()
		self.assertEqual([], self.servers)
