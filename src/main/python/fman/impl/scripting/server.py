"""Serve the authenticated local HTTP interface for scripting fman."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import logging
from threading import Thread
from urllib.parse import parse_qs, urlsplit

from fman.impl.scripting.config import (
	AUTHORIZATION_HEADER,
	COMMAND_PATH,
	COMMANDS_PATH,
	CLICK_PATH,
	DIALOG_PATH,
	FILES_PATH,
	KEYS_PATH,
	ORIGIN_HEADER,
	SCREENSHOT_PATH,
	STATE_PATH,
)
from fman.impl.scripting.actions import InvalidPane, UnknownCommand
from fman.impl.scripting.automation import UnknownFile
from fman.impl.util.qt.key_events import parse_chord


_LOG = logging.getLogger(__name__)
_MAX_BODY_SIZE = 1024 * 1024


class ScriptingServer:
	def __init__(self, config, token, actions, automation_actions=None):
		self._config = config
		self._token = token
		self._actions = actions
		self._automation_actions = automation_actions
		self._server = _ThreadingHTTPServer(
			(config.bind_address, config.port), self._make_handler()
		)
		self._server.daemon_threads = True
		self._thread = None

	@property
	def port(self):
		return self._server.server_address[1]

	def start(self):
		if self._thread is not None:
			return
		self._thread = Thread(target=self._server.serve_forever, daemon=True)
		self._thread.start()

	def stop(self):
		if self._thread is None:
			self._server.server_close()
			return
		self._server.shutdown()
		self._server.server_close()
		self._thread = None

	def _make_handler(self):
		server = self

		class Handler(BaseHTTPRequestHandler):
			def do_GET(self):
				if not self._authorize():
					return
				path = urlsplit(self.path)
				if path.path == STATE_PATH:
					self._send_json(200, server._actions.get_state())
				elif path.path == COMMANDS_PATH:
					self._send_json(200, server._actions.get_commands(server._config))
				elif path.path == SCREENSHOT_PATH:
					if not self._automation_enabled():
						return
					self._send_bytes(
						200, 'image/png', server._automation_actions.screenshot_png(),
					)
				elif path.path == DIALOG_PATH:
					if not self._automation_enabled():
						return
					self._send_json(200, {
						'dialog': server._automation_actions.get_dialog(),
					})
				elif path.path == FILES_PATH:
					if not self._automation_enabled():
						return
					query = parse_qs(path.query, keep_blank_values=True)
					pane_value = query.get('pane', ['0'])
					try:
						pane = int(pane_value[0])
						if len(pane_value) != 1:
							raise ValueError()
						files = server._automation_actions.get_visible_files(pane)
					except (ValueError, InvalidPane) as error:
						self._send_error(400, str(error) or 'pane must be an integer.')
					else:
						self._send_json(200, {'pane': pane, 'files': files})
				else:
					self._send_error(404, 'Unknown path.')

			def do_POST(self):
				if not self._authorize():
					return
				body = self._read_body()
				if body is None:
					return
				if urlsplit(self.path).path not in (
					COMMAND_PATH, KEYS_PATH, CLICK_PATH,
				):
					self._send_error(404, 'Unknown path.')
					return
				try:
					payload = json.loads(body.decode('utf-8'))
				except (UnicodeDecodeError, ValueError):
					self._send_error(400, 'Request body must be valid UTF-8 JSON.')
					return
				if not isinstance(payload, dict):
					self._send_error(400, 'Request body must be a JSON object.')
					return
				path = urlsplit(self.path).path
				if path in (KEYS_PATH, CLICK_PATH):
					if not self._automation_enabled():
						return
					if path == KEYS_PATH:
						self._keys(payload)
					else:
						self._click(payload)
					return
				name = payload.get('name')
				args = payload.get('args', {})
				pane = payload.get('pane')
				if not isinstance(name, str) or not name:
					self._send_error(400, 'name must be a non-empty string.')
					return
				if not isinstance(args, dict):
					self._send_error(400, 'args must be an object.')
					return
				if pane is not None and (
					not isinstance(pane, int) or isinstance(pane, bool)
				):
					self._send_error(400, 'pane must be an integer.')
					return
				if not server._config.is_command_allowed(name):
					self._send_error(403, 'Command is not allowed.')
					return
				try:
					server._actions.run_command(name, args, pane)
				except UnknownCommand:
					self._send_error(404, 'Unknown command.')
				except InvalidPane as error:
					self._send_error(400, str(error))
				else:
					self._send_json(200, {'ok': True})

			def _authorize(self):
				if not server._config.is_client_allowed(self.client_address[0]):
					self._send_error(403, 'Client address is not allowed.')
					return False
				if self.headers.get(ORIGIN_HEADER) is not None:
					self._send_error(403, 'Browser requests are not allowed.')
					return False
				authorization = self.headers.get(AUTHORIZATION_HEADER, '')
				prefix = 'Bearer '
				provided = (
					authorization[len(prefix):]
					if authorization.startswith(prefix) else '')
				if not hmac.compare_digest(provided, server._token):
					self._send_error(401, 'Missing or invalid bearer token.')
					return False
				return True

			def _automation_enabled(self):
				if server._config.automation:
					return True
				self._send_error(403, 'Automation is disabled.')
				return False

			def _keys(self, payload):
				keys = payload.get('keys')
				text = payload.get('text')
				if keys is None and text is None:
					self._send_error(400, 'Provide keys and/or text.')
					return
				if keys is not None:
					if not isinstance(keys, list) or any(
						not isinstance(key, str) for key in keys
					):
						self._send_error(400, 'keys must be a list of strings.')
						return
					try:
						for key in keys:
							parse_chord(key)
					except ValueError as error:
						self._send_error(400, str(error))
						return
				if text is not None and not isinstance(text, str):
					self._send_error(400, 'text must be a string.')
					return
				if keys is not None:
					server._automation_actions.send_keys(keys)
				if text is not None:
					server._automation_actions.type_text(text)
				self._send_json(200, {'ok': True})

			def _click(self, payload):
				button = payload.get('button', 'left')
				double = payload.get('double', False)
				has_file = 'file' in payload
				has_coordinates = 'x' in payload or 'y' in payload
				if has_file == has_coordinates:
					self._send_error(400, 'Provide file or x and y, but not both.')
					return
				if button not in ('left', 'right'):
					self._send_error(400, 'button must be left or right.')
					return
				if not isinstance(double, bool):
					self._send_error(400, 'double must be a boolean.')
					return
				if has_file:
					pane = payload.get('pane', 0)
					file_url = payload.get('file')
					if not isinstance(pane, int) or isinstance(pane, bool):
						self._send_error(400, 'pane must be an integer.')
						return
					if not isinstance(file_url, str) or not file_url:
						self._send_error(400, 'file must be a non-empty string.')
						return
					try:
						server._automation_actions.click_file(
							pane, file_url, button, double)
					except InvalidPane as error:
						self._send_error(400, str(error))
						return
					except UnknownFile:
						self._send_error(404, 'Unknown file.')
						return
				else:
					x, y = payload.get('x'), payload.get('y')
					if any(not isinstance(value, int) or isinstance(value, bool)
						for value in (x, y)):
						self._send_error(400, 'x and y must be integers.')
						return
					server._automation_actions.click_at(x, y, button, double)
				self._send_json(200, {'ok': True})

			def _read_body(self):
				length = self.headers.get('Content-Length', '0')
				try:
					length = int(length)
				except ValueError:
					self._send_error(400, 'Content-Length must be an integer.')
					return None
				if length < 0:
					self._send_error(400, 'Content-Length must not be negative.')
					return None
				if length > _MAX_BODY_SIZE:
					self._send_error(413, 'Request body is too large.')
					return None
				return self.rfile.read(length)

			def _send_json(self, status, value):
				body = json.dumps(value).encode('utf-8')
				self._send_bytes(status, 'application/json; charset=utf-8', body)

			def _send_bytes(self, status, content_type, body):
				self.send_response(status)
				self.send_header('Content-Type', content_type)
				self.send_header('Content-Length', str(len(body)))
				self.end_headers()
				self.wfile.write(body)

			def _send_error(self, status, message):
				self._send_json(status, {'error': message})

			def log_message(self, format_, *args):
				_LOG.debug('HTTP request: ' + format_, *args)

		return Handler


class _ThreadingHTTPServer(ThreadingHTTPServer):
	allow_reuse_address = True
