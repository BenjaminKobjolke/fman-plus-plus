"""Owns the scripting API server's application-level start and stop lifecycle."""

import logging

from .config import (
	ENABLED_KEY,
	SETTING_KEY,
	STATUS_OFF,
	STATUS_ON,
	STATUS_START_FAILED,
	ScriptingApiConfig,
	load_or_create_token,
)

_LOG = logging.getLogger(__name__)


class ScriptingApiControl:
	def __init__(self, local_settings, token_path, server_factory):
		self._local_settings = local_settings
		self._token_path = token_path
		self._server_factory = server_factory
		self._server = None

	@property
	def is_running(self):
		return self._server is not None

	def start(self):
		config = ScriptingApiConfig.from_settings(self._local_settings)
		token = load_or_create_token(self._token_path)
		server = self._server_factory(config, token)
		try:
			server.start()
		except OSError:
			_LOG.exception('Could not start scripting API server.')
			raise
		self._server = server

	def stop(self):
		if self._server is None:
			return
		server, self._server = self._server, None
		server.stop()

	def toggle(self):
		if self.is_running:
			self.stop()
			self._save_enabled(False)
			return STATUS_OFF
		try:
			self.start()
		except OSError as error:
			return STATUS_START_FAILED.format(error=error)
		self._save_enabled(True)
		config = ScriptingApiConfig.from_settings(self._local_settings)
		return STATUS_ON.format(
			address=config.bind_address,
			port=config.port,
			token_path=self._token_path,
		)

	def _save_enabled(self, enabled):
		settings = self._local_settings.get(SETTING_KEY, {})
		updated = dict(settings) if isinstance(settings, dict) else {}
		updated[ENABLED_KEY] = enabled
		self._local_settings[SETTING_KEY] = updated
		self._local_settings.flush()
