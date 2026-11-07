"""Read public plugin repositories from Forgejo's v1 API."""
from core.github import DESCRIPTION_FILE
from core.net import get_bytes
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit

import json


class ForgejoRepo:
	"""Forgejo repository adapted to the Install Plugin interface."""
	source = 'forgejo'

	def __init__(self, base_url: str, data: dict) -> None:
		self._base_url = base_url.rstrip('/')
		self._data = data
		self.location = data['html_url']
		self.hint = 'Codeberg · %d ★' % data.get('stars_count', 0)
		if 'codeberg.org' not in self._base_url:
			self.hint = '%s · %d ★' % (
				urlsplit(self._base_url).hostname, data.get('stars_count', 0)
			)
		if not data.get('stars_count'):
			self.hint = self.hint.split(' ·')[0]

	@property
	def name(self) -> str:
		return self._data['name']

	@property
	def description(self) -> str:
		return self._data.get('description') or ''

	@property
	def num_stars(self) -> int:
		return self._data.get('stars_count', 0)

	def fetch_description(self) -> str | None:
		owner, name = self._owner_and_name()
		branch = quote(self._data.get('default_branch') or '', safe='')
		url = '%s/api/v1/repos/%s/%s/raw/%s?ref=%s' % (
			self._base_url, quote(owner, safe=''), quote(name, safe=''),
			quote(DESCRIPTION_FILE, safe=''), branch
		)
		try:
			return _get(url).decode('utf-8')
		except HTTPError as error:
			if error.code != 404:
				raise
			return None
		except (URLError, UnicodeDecodeError):
			return None

	def get_latest_release(self) -> str:
		owner, name = self._owner_and_name()
		try:
			data = _get_json('%s/api/v1/repos/%s/%s/releases/latest' % (
				self._base_url, quote(owner, safe=''), quote(name, safe='')
			))
		except HTTPError as error:
			if error.code == 404:
				raise LookupError() from error
			raise
		return data['tag_name']

	def get_latest_commit(self) -> str:
		owner, name = self._owner_and_name()
		commits = _get_json('%s/api/v1/repos/%s/%s/commits?limit=1&stat=false' % (
			self._base_url, quote(owner, safe=''), quote(name, safe='')
		))
		return commits[0]['sha']

	def download_zipball(self, ref: str) -> bytes:
		owner, name = self._owner_and_name()
		return _get('%s/api/v1/repos/%s/%s/archive/%s.zip' % (
			self._base_url, quote(owner, safe=''), quote(name, safe=''),
			quote(ref, safe='')
		))

	def _owner_and_name(self) -> tuple[str, str]:
		owner = self._data['owner']['login']
		return owner, self._data['name']


def search(host: str, query: str, limit: int = 50) -> tuple[ForgejoRepo, ...]:
	# shortcut: Forgejo search accepts one topic and no text alongside
	# topic=true; the Install Plugin picker filters names locally.
	params = urlencode({
		'q': 'fman', 'topic': 'true', 'archived': 'false', 'sort': 'updated',
		'order': 'desc', 'limit': limit
	})
	data = _get_json(host.rstrip('/') + '/api/v1/repos/search?' + params)
	return tuple(
		ForgejoRepo(host, repo) for repo in data.get('data', [])
		if 'plugin' in repo.get('topics', [])
	)


def fetch(location: str) -> ForgejoRepo:
	parsed = urlsplit(location)
	parts = parsed.path.strip('/').split('/')
	if (
		parsed.scheme != 'https' or not parsed.netloc
		or len(parts) != 2 or not all(parts)
	):
		raise ValueError('Forgejo plugin location must be an https repository URL')
	base_url = 'https://' + parsed.netloc
	api_url = '%s/api/v1/repos/%s/%s' % (
		base_url, quote(parts[0], safe=''), quote(parts[1], safe='')
	)
	return ForgejoRepo(base_url, _get_json(api_url))


def _get_json(url: str):
	return json.loads(_get(url).decode('utf-8'))


def _get(url: str) -> bytes:
	return get_bytes(url)
