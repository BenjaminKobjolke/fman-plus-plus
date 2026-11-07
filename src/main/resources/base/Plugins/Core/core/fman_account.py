"""Credential storage and browser sign-in for a fman account."""
from core.fman_api import FmanApiAuthError, FmanApiClient
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

import keyring
import time


_KEYRING_SERVICE = 'fman++ API'
_KEYRING_USERNAME = 'access_token'
_SIGN_IN_TIMEOUT_SECONDS = 5 * 60
_SIGN_IN_POLL_SECONDS = 2


def load_token() -> str | None:
	return keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)


def save_token(token: str) -> None:
	if not isinstance(token, str) or not token:
		raise ValueError('An access token is required')
	keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, token)


def clear_token() -> None:
	try:
		keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
	except keyring.errors.PasswordDeleteError:
		pass


def sign_in(client):
	"""Open XIDA sign-in and poll its callback until it returns an access token.

	The deployed service rejects loopback redirect URLs. Without a redirect URL,
	XIDA shows its own completion page and the desktop app polls by register code.
	"""
	auth = client.start_sign_in()
	QDesktopServices.openUrl(QUrl(auth.oauth_url))
	deadline = time.monotonic() + _SIGN_IN_TIMEOUT_SECONDS
	while True:
		try:
			result = client.finish_sign_in(auth.register_code)
		except FmanApiAuthError:
			if time.monotonic() >= deadline:
				raise TimeoutError('Timed out waiting for fman account sign-in')
			time.sleep(min(_SIGN_IN_POLL_SECONDS, max(0, deadline - time.monotonic())))
			continue
		save_token(result.access_token)
		return result


def signed_in_client():
	"""Return a client with a freshly refreshed token, or None when signed out."""
	token = load_token()
	if not token:
		return None
	client = FmanApiClient(token)
	try:
		result = client.refresh()
	except FmanApiAuthError:
		clear_token()
		return None
	save_token(result.access_token)
	return FmanApiClient(result.access_token)
