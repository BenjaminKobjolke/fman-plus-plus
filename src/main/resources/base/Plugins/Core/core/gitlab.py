"""Read public plugin repositories from GitLab's v4 API."""
from core.github import DESCRIPTION_FILE
from core.net import get_bytes
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit

import json


class GitLabProject:
	"""GitLab project adapted to the interface used by Install Plugin."""
	source = 'gitlab'

	def __init__(self, base_url: str, data: dict) -> None:
		self._base_url = base_url.rstrip('/')
		self._data = data
		self.location = data['web_url']
		self.hint = 'GitLab · %d ★' % data.get('star_count', 0)
		if not data.get('star_count'):
			self.hint = 'GitLab'

	@property
	def name(self) -> str:
		return self._data['path']

	@property
	def description(self) -> str:
		return self._data.get('description') or ''

	@property
	def num_stars(self) -> int:
		return self._data.get('star_count', 0)

	def fetch_description(self) -> str | None:
		project_id = quote(str(self._data['id']), safe='')
		branch = quote(self._data.get('default_branch') or '', safe='')
		url = '%s/api/v4/projects/%s/repository/files/%s/raw?ref=%s' % (
			self._base_url, project_id, quote(DESCRIPTION_FILE, safe=''), branch
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
		try:
			data = _get_json(self._api_url(
				'/releases/permalink/latest'
			))
		except HTTPError as error:
			if error.code == 404:
				raise LookupError() from error
			raise
		return data['tag_name']

	def get_latest_commit(self) -> str:
		commits = _get_json(self._api_url(
			'/repository/commits?per_page=1'
		))
		return commits[0]['id']

	def download_zipball(self, ref: str) -> bytes:
		return _get(self._api_url(
			'/repository/archive.zip?sha=' + quote(ref, safe='')
		))

	def _api_url(self, suffix: str) -> str:
		return '%s/api/v4/projects/%s%s' % (
			self._base_url, quote(str(self._data['id']), safe=''), suffix
		)


def search(host: str, query: str, limit: int = 20) -> tuple[GitLabProject, ...]:
	params = urlencode({
		'topic': 'fman,plugin', 'search': query, 'archived': 'false',
		'order_by': 'last_activity_at', 'sort': 'desc', 'per_page': limit
	})
	data = _get_json(host.rstrip('/') + '/api/v4/projects?' + params)
	return tuple(GitLabProject(host, project) for project in data)


def fetch(location: str) -> GitLabProject:
	parsed = urlsplit(location)
	if parsed.scheme != 'https' or not parsed.netloc or not parsed.path.strip('/'):
		raise ValueError('GitLab plugin location must be an https repository URL')
	# shortcut: self-hosted GitLab installations under a sub-path are not
	# supported because sync derives the API base from the location's host.
	base_url = 'https://' + parsed.netloc
	project_path = parsed.path.strip('/')
	api_path = quote(project_path, safe='')
	data = _get_json(base_url + '/api/v4/projects/' + api_path)
	return GitLabProject(base_url, data)


def _get_json(url: str):
	return json.loads(_get(url).decode('utf-8'))


def _get(url: str) -> bytes:
	return get_bytes(url)
