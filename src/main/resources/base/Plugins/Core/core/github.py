from core.net import get_bytes
from urllib.error import HTTPError, URLError

import json
import re
import sys

DESCRIPTION_FILE = 'description.md'

def find_repos(topics):
	# Archived repos are read-only, so their plugin can never be updated.
	# Filter server-side so total_count - and thus paging - stays correct.
	query = '+'.join('topic:' + topic for topic in topics) + '+archived:false'
	url = "https://api.github.com/search/repositories?q=" + query
	repos = map(GitHubRepo, _fetch_all_pages(url))
	# Newest first, most-starred among equally recent ones. GitHub's default is
	# relevance, which for a pure topic query is near-uniform and thus
	# arbitrary. Sorting here and not via the API's sort=updated because that is
	# the repo's metadata date - a description edit makes an abandoned plugin
	# look fresh. pushed_at is the last commit.
	return sorted(
		repos, key=lambda repo: (repo.last_modified, repo.num_stars),
		reverse=True
	)

def _fetch_all_pages(json_url, page_size=100):
	for page in range(1, sys.maxsize):
		data = _get_json(json_url + '&per_page=%d&page=%d' % (page_size, page))
		yield from data['items']
		has_more = page * page_size < data['total_count']
		if not has_more:
			break

class GitHubRepo:
	@classmethod
	def fetch(cls, repo):
		url = 'https://api.github.com/repos/' + repo
		return cls(_get_json(url))
	def __init__(self, data):
		self._data = data
	def __str__(self):
		return self._data['full_name']
	def __repr__(self):
		return '<%s: %s>' % (self.__class__.__name__, self)
	@property
	def num_stars(self):
		return self._data['stargazers_count']
	@property
	def name(self):
		return self._data['name']
	@property
	def description(self):
		return self._data['description']
	@property
	def url(self):
		return self._data['url']
	@property
	def last_modified(self):
		# ISO-8601 UTC, so lexicographic order is chronological order. '' for
		# a repo that was never pushed to, which sorts before any date.
		return self._data.get('pushed_at') or ''
	def get_latest_release(self):
		try:
			data = _get_json(self._url('releases', id='latest'))
		except HTTPError as e:
			if e.code == 404:
				raise LookupError()
			raise
		return data['tag_name']
	def get_latest_commit(self):
		return _get_json(self._url('commits'))[0]['sha']
	def download_zipball(self, ref):
		zipball_url = self._url('archive', archive_format='zipball', ref=ref)
		return _get(zipball_url)
	def fetch_description(self):
		url = 'https://raw.githubusercontent.com/%s/%s/%s' % (
			self, self._data['default_branch'], DESCRIPTION_FILE
		)
		try:
			return _get(url).decode('utf-8')
		except (URLError, UnicodeDecodeError):
			# Plugins need not provide a description, and network errors are normal.
			return None
	def _url(self, name, **kwargs):
		url = self._data[name + '_url']
		required_url_params = re.finditer(r'{([^/][^}]+)}', url)
		for match in required_url_params:
			url = url.replace(match.group(0), kwargs[match.group(1)])
		optional_url_params = re.finditer(r'{/([^}]+)}', url)
		for match in optional_url_params:
			param = match.group(1)
			value = '/' + kwargs[param] if param in kwargs else ''
			url = url.replace(match.group(0), value)
		return url

def _get_json(url):
	return json.loads(_get(url).decode('utf-8'))

def _get(url):
	return get_bytes(url)
