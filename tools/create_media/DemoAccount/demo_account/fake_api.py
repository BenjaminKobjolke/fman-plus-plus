"""In-memory HTTP responses for the demo-only fman account plugin."""

import json


_API_PREFIX = '/api/v1'
_DEMO_USER = {'email': 'ada@example.com'}
_SETTINGS_UPDATED_AT = '2026-01-01T00:00:00+00:00'


def respond(method, path, body):
	"""Return an HTTP status and JSON body for one supported fake API route."""
	method = method.lower()
	if not path.startswith(_API_PREFIX + '/'):
		return 503, {}

	route = path[len(_API_PREFIX):]
	if method == 'post' and route == '/auth/init':
		return 200, {'register_code': 'demo', 'oauth_url': 'about:blank'}
	if method == 'post' and route in ('/auth/callback', '/auth/refresh'):
		return 200, {'access_token': 'demo-token', 'user': _DEMO_USER.copy()}
	if method == 'get' and route == '/auth/me':
		return 200, {
			'user': {'name': 'Ada Demo', 'email': 'ada@example.com'}
		}
	if method == 'get' and route == '/plugin-list':
		return 200, {'plugins': []}

	parts = route.split('/')
	if len(parts) == 4 and parts[:2] == ['', 'settings']:
		if method == 'get':
			return 404, {}
		if method == 'put' and isinstance(body, dict) and 'content' in body:
			return 200, {
				'os': parts[2],
				'kind': parts[3],
				'revision': 1,
				'content': body['content'],
				'updated_at': _SETTINGS_UPDATED_AT,
			}

	return 503, {}


class FakeResponse:
	"""Small requests.Response substitute used by the demo account plugin."""

	def __init__(self, status_code, data):
		self.status_code = status_code
		self._data = data
		self.text = json.dumps(data)

	def json(self):
		return self._data
