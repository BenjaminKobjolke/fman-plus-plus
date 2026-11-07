from core.fman_api import FmanApiAuthError, FmanApiClient, FmanApiError
from core.plugin_list import PluginListEntry, PluginOs, PluginSource
from unittest import TestCase
from unittest.mock import Mock

import hashlib


class FmanApiClientTest(TestCase):
	def setUp(self):
		self.session = Mock()
		self.client = FmanApiClient('access-token', session=self.session)

	def test_sends_bearer_header_and_parses_complete_plugin_list(self):
		self.session.get.return_value = _response({
			'plugins': [_entry_json()], 'total': 1, 'limit': 200, 'offset': 0
		})
		entries = self.client.get_plugin_list()
		self.assertEqual((_entry(),), entries)
		self.session.get.assert_called_once_with(
			'https://fman.workflow-tools.com/api/v1/plugin-list',
			params={'limit': 200}, headers={'Authorization': 'Bearer access-token'},
			timeout=30
		)

	def test_put_plugin_sends_entry_json_and_returns_typed_entry(self):
		self.session.put.return_value = _response(_entry_json())
		self.assertEqual(_entry(), self.client.put_plugin(_entry()))
		self.session.put.assert_called_once_with(
			'https://fman.workflow-tools.com/api/v1/plugin-list/Example',
			json=_entry().to_json(), headers={'Authorization': 'Bearer access-token'},
			timeout=30
		)

	def test_delete_plugin_accepts_no_content(self):
		self.session.delete.return_value = _response(None, status_code=204)
		self.client.delete_plugin('Example')
		self.session.delete.assert_called_once()

	def test_unauthorized_response_raises_auth_error(self):
		self.session.get.return_value = _response(
			{'message': 'expired'}, status_code=401
		)
		with self.assertRaises(FmanApiAuthError):
			self.client.get_plugin_list()

	def test_other_error_response_raises_api_error(self):
		self.session.get.return_value = _response(
			{'message': 'server error'}, status_code=500
		)
		with self.assertRaises(FmanApiError):
			self.client.get_plugin_list()

	def test_download_release_checks_sha256(self):
		contents = b'zip bytes'
		response = _response(None, content=contents, headers={
			'X-Content-SHA256': hashlib.sha256(contents).hexdigest()
		})
		self.session.get.return_value = response
		self.assertEqual(contents, self.client.download_release('Example', 'v1.0'))
		self.session.get.assert_called_once_with(
			'https://fman.workflow-tools.com/api/v1/plugins/Example/releases/v1.0/download',
			headers={}, timeout=30
		)

	def test_download_release_rejects_sha256_mismatch(self):
		self.session.get.return_value = _response(None, content=b'zip bytes', headers={
			'X-Content-SHA256': '0' * 64
		})
		with self.assertRaises(FmanApiError):
			self.client.download_release('Example', 'v1.0')

	def test_search_catalog_passes_query_and_limit(self):
		self.session.get.return_value = _response({'plugins': [{
			'name': 'Example', 'description': 'An example plugin'
		}], 'total': 1})
		plugins = self.client.search_catalog('exam', limit=7)
		self.assertEqual('Example', plugins[0].name)
		self.session.get.assert_called_once_with(
			'https://fman.workflow-tools.com/api/v1/plugins',
			params={'q': 'exam', 'limit': 7},
			headers={}, timeout=30
		)

	def test_get_catalog_releases_parses_versions_without_authentication(self):
		self.session.get.return_value = _response({'releases': [
			{'version': '2.0'}, {'version': '1.0'}
		]})

		self.assertEqual(('2.0', '1.0'), tuple(
			release.version for release in self.client.get_catalog_releases('Example')
		))
		self.session.get.assert_called_once_with(
			'https://fman.workflow-tools.com/api/v1/plugins/Example/releases',
			headers={}, timeout=30
		)

	def test_catalog_plugin_url_uses_configured_api_base_url(self):
		client = FmanApiClient(
			base_url='https://api.example.test/', session=self.session
		)

		self.assertEqual(
			'https://api.example.test/api/v1/plugins/Example%20Plugin',
			client.catalog_plugin_url('Example Plugin')
		)


class FmanApiAuthTest(TestCase):
	def test_auth_init_and_callback_are_typed(self):
		session = Mock()
		session.post.side_effect = [
			_response({'register_code': 'code', 'oauth_url': 'https://login.example'}),
			_response({'access_token': 'token', 'user': {'email': 'user@example.com'}})
		]
		client = FmanApiClient(session=session)
		init = client.start_sign_in('http://127.0.0.1:54321/fman-signin')
		self.assertEqual('code', init.register_code)
		result = client.finish_sign_in('code')
		self.assertEqual('token', result.access_token)
		self.assertEqual('user@example.com', result.email)


def _entry():
	return PluginListEntry(
		'Example', PluginSource.GITHUB, 'https://github.com/example/plugin',
		'v1.0', PluginOs.WINDOWS, '2.1.4'
	)


def _entry_json():
	return _entry().to_json()


def _response(data, status_code=200, content=b'', headers=None):
	response = Mock()
	response.status_code = status_code
	response.headers = headers or {}
	response.content = content
	response.json.return_value = data
	response.text = '' if data is None else str(data)
	return response
