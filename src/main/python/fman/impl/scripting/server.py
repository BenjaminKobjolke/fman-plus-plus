"""Serve the authenticated local HTTP interface for scripting fman."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import logging
from threading import Thread

from fman.impl.scripting.config import (
	AUTHORIZATION_HEADER,
	COMMAND_PATH,
	COMMANDS_PATH,
	ORIGIN_HEADER,
	STATE_PATH,
)
from fman.impl.scripting.actions import InvalidPane, UnknownCommand


_LOG = logging.getLogger(__name__)
_MAX_BODY_SIZE = 1024 * 1024


class ScriptingServer:
	def __init__(self, config, token, actions):
		self._config = config
		self._token = token
		self._actions = actions
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
				if self.path == STATE_PATH:
					self._send_json(200, server._actions.get_state())
				elif self.path == COMMANDS_PATH:
					self._send_json(200, server._actions.get_commands(server._config))
				else:
					self._send_error(404, 'Unknown path.')

			def do_POST(self):
				if not self._authorize():
					return
				body = self._read_body()
				if body is None:
					return
				if self.path != COMMAND_PATH:
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
				self.send_response(status)
				self.send_header('Content-Type', 'application/json; charset=utf-8')
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
