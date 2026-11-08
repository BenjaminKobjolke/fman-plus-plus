from core.fman_api import (
	FmanApiAuthError, FmanApiClient, FmanApiConflictError, FmanApiError,
	SyncedSettingsDocument,
)
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

	def test_skips_unknown_plugin_source_and_keeps_supported_entries(self):
		valid = _entry_json()
		unknown = dict(valid, name='Future', source='future-host')
		self.session.get.return_value = _response({'plugins': [unknown, valid]})
		self.assertEqual((_entry(),), self.client.get_plugin_list())

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

	def test_get_settings_sends_bearer_header_and_parses_document(self):
		self.session.get.return_value = _response(_settings_json())

		self.assertEqual(
			_settings_document(), self.client.get_settings('Windows', 'key_bindings')
		)
		self.session.get.assert_called_once_with(
			'https://fman.workflow-tools.com/api/v1/settings/Windows/key_bindings',
			headers={'Authorization': 'Bearer access-token'}, timeout=30
		)

	def test_get_settings_returns_none_for_404(self):
		self.session.get.return_value = _response(
			{'message': 'not found'}, status_code=404
		)

		self.assertIsNone(self.client.get_settings('Windows', 'key_bindings'))

	def test_put_settings_sends_base_revision_and_content(self):
		self.session.put.return_value = _response(_settings_json())

		self.assertEqual(
			_settings_document(),
			self.client.put_settings('Windows', 'key_bindings', 2, [{'keys': 'Ctrl+A'}])
		)
		self.session.put.assert_called_once_with(
			'https://fman.workflow-tools.com/api/v1/settings/Windows/key_bindings',
			json={'base_revision': 2, 'content': [{'keys': 'Ctrl+A'}]},
			headers={'Authorization': 'Bearer access-token'}, timeout=30
		)

	def test_put_settings_raises_conflict_with_current_document(self):
		self.session.put.return_value = _response(
			{'current': _settings_json()}, status_code=409
		)

		with self.assertRaises(FmanApiConflictError) as caught:
			self.client.put_settings('Windows', 'key_bindings', 2, [])

		self.assertEqual(_settings_document(), caught.exception.current)

	def test_put_settings_raises_conflict_with_null_current_document(self):
		self.session.put.return_value = _response({'current': None}, status_code=409)

		with self.assertRaises(FmanApiConflictError) as caught:
			self.client.put_settings('Windows', 'key_bindings', None, [])

		self.assertIsNone(caught.exception.current)


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


def _settings_document():
	return SyncedSettingsDocument.from_json(_settings_json())


def _settings_json():
	return {
		'os': 'Windows', 'kind': 'key_bindings', 'revision': 3,
		'content': [{'keys': 'Ctrl+A'}], 'updated_at': '2026-11-08T20:00:00+00:00'
	}


def _response(data, status_code=200, content=b'', headers=None):
	response = Mock()
	response.status_code = status_code
	response.headers = headers or {}
	response.content = content
	response.json.return_value = data
	response.text = '' if data is None else str(data)
	return response
