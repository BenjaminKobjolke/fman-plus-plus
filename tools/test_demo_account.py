import sys
import types
import unittest
from pathlib import Path


DEMO_PLUGIN_ROOT = Path(__file__).parent / 'create_media' / 'DemoAccount'
sys.path.insert(0, str(DEMO_PLUGIN_ROOT))
# The plugin entry point imports fman Core and Qt at startup. These tests cover
# only the pure router, so provide its package path without loading that entry point.
demo_account_package = types.ModuleType('demo_account')
demo_account_package.__path__ = [str(DEMO_PLUGIN_ROOT / 'demo_account')]
sys.modules['demo_account'] = demo_account_package

from demo_account.fake_api import respond  # noqa: E402


class FakeApiTest(unittest.TestCase):
	def test_auth_routes_return_demo_account_data(self):
		cases = [
			('post', '/api/v1/auth/init', {'register_code', 'oauth_url'}),
			('post', '/api/v1/auth/callback', {'access_token', 'user'}),
			('post', '/api/v1/auth/refresh', {'access_token', 'user'}),
			('get', '/api/v1/auth/me', {'user'}),
			('get', '/api/v1/plugin-list', {'plugins'}),
		]
		for method, path, keys in cases:
			with self.subTest(path=path):
				status, data = respond(method, path, None)
				self.assertEqual(status, 200)
				self.assertTrue(keys <= data.keys())

	def test_missing_settings_return_404(self):
		status, data = respond(
			'get', '/api/v1/settings/Windows/key_bindings', None
		)
		self.assertEqual(status, 404)
		self.assertEqual(data, {})

	def test_settings_put_echoes_content_with_revision(self):
		content = [{'keys': 'Ctrl+A'}]
		status, data = respond(
			'put', '/api/v1/settings/Windows/key_bindings',
			{'base_revision': None, 'content': content}
		)
		self.assertEqual(status, 200)
		self.assertEqual(data['content'], content)
		self.assertEqual(data['revision'], 1)

	def test_unknown_path_is_unavailable(self):
		self.assertEqual(respond('get', '/api/v1/unexpected', None), (503, {}))


if __name__ == '__main__':
	unittest.main()
