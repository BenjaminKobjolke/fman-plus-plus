"""Typed client for the fman account and plugin catalog API."""
from core.plugin_list import PluginListEntry
from dataclasses import dataclass
from urllib.parse import quote
from typing import Any

import hashlib
import requests


_API_V1 = '/api/v1'
_TIMEOUT_SECONDS = 30


class FmanApiError(Exception):
	"""An unsuccessful or malformed fman API response."""


class FmanApiAuthError(FmanApiError):
	"""The stored account token was rejected by the API."""


@dataclass(frozen=True)
class AuthInitResponse:
	register_code: str
	oauth_url: str


@dataclass(frozen=True)
class AuthCallbackResponse:
	access_token: str
	email: str | None = None


@dataclass(frozen=True)
class CatalogPluginInfo:
	name: str
	description: str


@dataclass(frozen=True)
class CatalogReleaseInfo:
	version: str


class FmanApiClient:
	def __init__(self, token: str | None = None, base_url: str | None = None,
			session: Any = None) -> None:
		from fman import links
		self._token = token
		self._base_url = (base_url or links.FMAN_API).rstrip('/')
		self._session = session or requests.Session()

	def start_sign_in(self, redirect_url: str | None = None) -> AuthInitResponse:
		payload = {}
		if redirect_url is not None:
			payload['redirect_url'] = redirect_url
		response = self._request(
			'post', _API_V1 + '/auth/init', json=payload, authenticated=False
		)
		data = self._json_object(response)
		try:
			return AuthInitResponse(data['register_code'], data['oauth_url'])
		except (KeyError, TypeError) as e:
			raise FmanApiError('Invalid auth init response') from e

	def finish_sign_in(self, register_code: str) -> AuthCallbackResponse:
		response = self._request(
			'post', _API_V1 + '/auth/callback',
			json={'register_code': register_code}, authenticated=False
		)
		return self._auth_response(response)

	def refresh(self) -> AuthCallbackResponse:
		response = self._request('post', _API_V1 + '/auth/refresh', json={})
		return self._auth_response(response)

	def get_plugin_list(self) -> tuple[PluginListEntry, ...]:
		response = self._request(
			'get', _API_V1 + '/plugin-list', params={'limit': 200}
		)
		data = self._json_object(response)
		plugins = data.get('plugins')
		if not isinstance(plugins, list):
			raise FmanApiError('Invalid plugin list response: plugins must be a list')
		try:
			return tuple(PluginListEntry.from_json(plugin) for plugin in plugins)
		except (TypeError, ValueError) as e:
			raise FmanApiError('Invalid plugin list entry: %s' % e) from e

	def put_plugin(self, entry: PluginListEntry) -> PluginListEntry:
		if not isinstance(entry, PluginListEntry):
			raise TypeError('entry must be a PluginListEntry')
		path = _API_V1 + '/plugin-list/' + quote(entry.name, safe='')
		response = self._request('put', path, json=entry.to_json())
		return self._plugin_entry(response)

	def delete_plugin(self, name: str) -> None:
		path = _API_V1 + '/plugin-list/' + quote(name, safe='')
		self._request('delete', path)

	def search_catalog(
		self, query: str, limit: int = 20
	) -> tuple[CatalogPluginInfo, ...]:
		response = self._request(
			'get', _API_V1 + '/plugins', authenticated=False,
			params={'q': query, 'limit': limit}
		)
		data = self._json_object(response)
		plugins = data.get('plugins')
		if not isinstance(plugins, list):
			raise FmanApiError('Invalid catalog response: plugins must be a list')
		try:
			return tuple(CatalogPluginInfo(
				name=plugin['name'], description=plugin.get('description') or ''
			) for plugin in plugins)
		except (KeyError, TypeError) as e:
			raise FmanApiError('Invalid catalog plugin response') from e

	def get_catalog_releases(self, name: str) -> tuple[CatalogReleaseInfo, ...]:
		path = _API_V1 + '/plugins/' + quote(name, safe='') + '/releases'
		response = self._request('get', path, authenticated=False)
		data = self._json_object(response)
		releases = data.get('releases')
		if not isinstance(releases, list):
			raise FmanApiError('Invalid catalog releases response')
		try:
			return tuple(CatalogReleaseInfo(release['version']) for release in releases)
		except (KeyError, TypeError) as e:
			raise FmanApiError('Invalid catalog release response') from e

	def catalog_plugin_url(self, name: str) -> str:
		return self._base_url + _API_V1 + '/plugins/' + quote(name, safe='')

	def download_release(self, name: str, version: str) -> bytes:
		path = '%s/plugins/%s/releases/%s/download' % (
			_API_V1, quote(name, safe=''), quote(version, safe='')
		)
		response = self._request('get', path, authenticated=False)
		contents = response.content
		expected_hash = response.headers.get('X-Content-SHA256')
		actual_hash = hashlib.sha256(contents).hexdigest()
		if not expected_hash or actual_hash.lower() != expected_hash.strip().lower():
			raise FmanApiError('Downloaded plugin release failed its SHA-256 check')
		return contents

	def _plugin_entry(self, response: Any) -> PluginListEntry:
		try:
			return PluginListEntry.from_json(self._json_object(response))
		except ValueError as e:
			raise FmanApiError('Invalid plugin list entry: %s' % e) from e

	def _auth_response(self, response: Any) -> AuthCallbackResponse:
		data = self._json_object(response)
		try:
			user = data.get('user') or {}
			return AuthCallbackResponse(
				access_token=data['access_token'], email=user.get('email')
			)
		except (KeyError, AttributeError, TypeError) as e:
			raise FmanApiError('Invalid auth callback response') from e

	def _request(self, method: str, path: str, authenticated: bool = True,
			**kwargs: Any) -> Any:
		url = self._base_url + path
		headers = dict(kwargs.pop('headers', {}))
		if authenticated:
			if not self._token:
				raise FmanApiAuthError('No fman account token is available')
			headers['Authorization'] = 'Bearer ' + self._token
		try:
			response = getattr(self._session, method)(
				url, headers=headers, timeout=_TIMEOUT_SECONDS, **kwargs
			)
		except requests.RequestException as e:
			raise FmanApiError('Could not reach the fman API: %s' % e) from e
		if response.status_code == 401:
			raise FmanApiAuthError('The fman account token was rejected')
		if not 200 <= response.status_code < 300:
			raise FmanApiError(
				'fman API returned HTTP %d: %s' % (
					response.status_code, response.text
				)
			)
		return response

	@staticmethod
	def _json_object(response):
		try:
			data = response.json()
		except (ValueError, TypeError) as e:
			raise FmanApiError('fman API returned invalid JSON') from e
		if not isinstance(data, dict):
			raise FmanApiError('fman API response must be a JSON object')
		return data
