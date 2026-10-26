import json
from dataclasses import replace
from unittest import TestCase
from unittest.mock import MagicMock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fman.impl.scripting.actions import InvalidPane, ScriptingActions, UnknownCommand
from fman.impl.scripting.config import ScriptingApiConfig
from fman.impl.scripting.server import ScriptingServer


class ScriptingServerTest(TestCase):
	TOKEN = 'secret-token'

	def setUp(self):
		config = replace(
			ScriptingApiConfig.from_settings(_Settings({})),
			port=0,
		)
		self.actions = MagicMock(spec=ScriptingActions)
		self.actions.get_state.return_value = {'active_pane': 0, 'panes': []}
		self.actions.get_commands.return_value = {
			'pane': ['open_directory'],
			'application': [],
			'allowed': ['open_directory'],
		}
		self.server = ScriptingServer(config, self.TOKEN, self.actions)
		self.server.start()
		self.base_url = 'http://127.0.0.1:%s' % self.server.port

	def tearDown(self):
		self.server.stop()

	def test_state_and_commands_routes_return_action_data(self):
		self.assertEqual(
			{'active_pane': 0, 'panes': []},
			self._request('GET', '/v1/state'),
		)
		self.assertEqual(
			self.actions.get_commands.return_value,
			self._request('GET', '/v1/commands'),
		)

	def test_command_route_dispatches_allowed_command(self):
		self.actions.run_command.return_value = None

		response = self._request('POST', '/v1/command', {
			'name': 'open_directory', 'args': {'url': 'file:///tmp'}, 'pane': 1,
		})

		self.assertEqual({'ok': True}, response)
		self.actions.run_command.assert_called_once_with(
			'open_directory', {'url': 'file:///tmp'}, 1,
		)

	def test_missing_and_wrong_tokens_are_rejected(self):
		for token in (None, 'wrong-token'):
			with self.subTest(token=token):
				self.assertEqual(401, self._request_error(
					'GET', '/v1/state', token=token,
				))

	def test_origin_header_is_rejected(self):
		self.assertEqual(403, self._request_error(
			'GET', '/v1/state', headers={'Origin': 'https://example.test'},
		))

	def test_disallowed_command_is_rejected_without_dispatch(self):
		self.assertEqual(403, self._request_error('POST', '/v1/command', {
			'name': 'delete_permanently',
		}))
		self.actions.run_command.assert_not_called()

	def test_unknown_command_and_path_are_not_found(self):
		self.actions.run_command.side_effect = UnknownCommand('missing')
		self.assertEqual(404, self._request_error('POST', '/v1/command', {
			'name': 'open_directory',
		}))
		self.assertEqual(404, self._request_error('GET', '/v1/missing'))

	def test_invalid_json_shape_and_pane_are_bad_requests(self):
		self.assertEqual(400, self._raw_error('POST', '/v1/command', b'{'))
		self.assertEqual(400, self._request_error('POST', '/v1/command', {
			'name': 'open_directory', 'args': [],
		}))
		self.actions.run_command.side_effect = InvalidPane('out of range')
		self.assertEqual(400, self._request_error('POST', '/v1/command', {
			'name': 'open_directory',
		}))

	def test_oversized_content_length_is_rejected(self):
		request = Request(
			self.base_url + '/v1/command',
			data=b'{}',
			headers=self._headers(),
			method='POST',
		)
		request.add_header('Content-Length', str(1024 * 1024 + 1))
		with self.assertRaises(HTTPError) as caught:
			urlopen(request, timeout=3)
		self.assertEqual(413, caught.exception.code)

	def test_request_from_disallowed_client_is_rejected_by_config(self):
		config = ScriptingApiConfig.from_settings(_Settings({
			'scripting_api': {'allowed_hosts': ['192.168.1.5']},
		}))
		self.assertFalse(config.is_client_allowed('192.168.1.6'))

	def _request(self, method, path, payload=None, token=TOKEN, headers=None):
		body = None if payload is None else json.dumps(payload).encode('utf-8')
		request_headers = self._headers(token)
		request_headers.update(headers or {})
		request = Request(
			self.base_url + path, data=body, headers=request_headers,
			method=method,
		)
		with urlopen(request, timeout=3) as response:
			return json.loads(response.read().decode('utf-8'))

	def _request_error(self, method, path, payload=None, token=TOKEN, headers=None):
		body = None if payload is None else json.dumps(payload).encode('utf-8')
		request_headers = self._headers(token)
		request_headers.update(headers or {})
		request = Request(
			self.base_url + path, data=body, headers=request_headers,
			method=method,
		)
		with self.assertRaises(HTTPError) as caught:
			urlopen(request, timeout=3)
		return caught.exception.code

	def _raw_error(self, method, path, body):
		request = Request(
			self.base_url + path, data=body, headers=self._headers(), method=method,
		)
		with self.assertRaises(HTTPError) as caught:
			urlopen(request, timeout=3)
		return caught.exception.code

	def _headers(self, token=TOKEN):
		headers = {}
		if token is not None:
			headers['Authorization'] = 'Bearer ' + token
		return headers


class _Settings:
	def __init__(self, values):
		self._values = values

	def get(self, key, default):
		return self._values.get(key, default)
