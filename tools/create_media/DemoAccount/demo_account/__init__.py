"""Demo-only account fake, seeded by run_fman_demo.bat for demo 16 only.

This plugin is never shipped with fman.
"""

import keyring
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

from core import fman_account, fman_api

from .fake_api import FakeResponse, respond


class _MemoryKeyring(KeyringBackend):
	"""Empty credential store local to the demo process."""

	def __init__(self):
		super().__init__()
		self._passwords = {}

	def get_password(self, service, username):
		return self._passwords.get((service, username))

	def set_password(self, service, username, password):
		self._passwords[(service, username)] = password

	def delete_password(self, service, username):
		try:
			del self._passwords[(service, username)]
		except KeyError:
			raise PasswordDeleteError(service, username) from None


class _FakeSession:
	"""Route every account API request to the in-memory fake."""

	def get(self, url, **kwargs):
		return self._respond('get', url, kwargs)

	def post(self, url, **kwargs):
		return self._respond('post', url, kwargs)

	def put(self, url, **kwargs):
		return self._respond('put', url, kwargs)

	def delete(self, url, **kwargs):
		return self._respond('delete', url, kwargs)

	@staticmethod
	def _respond(method, url, kwargs):
		from urllib.parse import urlsplit
		status, data = respond(method, urlsplit(url).path, kwargs.get('json'))
		return FakeResponse(status, data)


keyring.set_keyring(_MemoryKeyring())

_original_api_init = fman_api.FmanApiClient.__init__


def _fake_api_init(self, token=None, base_url=None, session=None):
	_original_api_init(
		self, token=token, base_url=base_url, session=_FakeSession()
	)


fman_api.FmanApiClient.__init__ = _fake_api_init


class _NoBrowser:
	@staticmethod
	def openUrl(url):
		return True


fman_account.QDesktopServices = _NoBrowser
