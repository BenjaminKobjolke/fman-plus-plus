"""Configure and search the supported GitLab and Forgejo plugin hosts."""
from core import forgejo, gitlab
from core.plugin_list import PluginSource
from core.settings import SETTINGS_FILE, get_setting
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit


PLUGIN_HOSTS_SETTING = 'plugin_hosts'


@dataclass(frozen=True)
class PluginHost:
	source: PluginSource
	base_url: str

	@property
	def label(self) -> str:
		hostname = urlsplit(self.base_url).hostname or self.base_url
		if hostname == 'gitlab.com':
			return 'GitLab'
		if hostname == 'codeberg.org':
			return 'Codeberg'
		return hostname


DEFAULT_HOSTS = (
	PluginHost(PluginSource.GITLAB, 'https://gitlab.com'),
	PluginHost(PluginSource.FORGEJO, 'https://codeberg.org'),
)


def configured_hosts() -> tuple[PluginHost, ...]:
	hosts = list(DEFAULT_HOSTS)
	configured = get_setting(SETTINGS_FILE, PLUGIN_HOSTS_SETTING, [])
	if not isinstance(configured, list):
		return tuple(hosts)
	known_sources = {
		'gitlab': PluginSource.GITLAB,
		'forgejo': PluginSource.FORGEJO,
	}
	known_urls = {host.base_url for host in hosts}
	for item in configured:
		if not isinstance(item, dict):
			continue
		type_name = item.get('type')
		source = known_sources.get(type_name) if isinstance(type_name, str) else None
		url = item.get('url')
		if source is None or not isinstance(url, str):
			continue
		try:
			parsed = urlsplit(url)
			hostname = parsed.hostname
		except ValueError:
			continue
		if (
			parsed.scheme != 'https' or not hostname
			or parsed.username or parsed.password
			or parsed.query or parsed.fragment or parsed.path not in ('', '/')
		):
			continue
		base_url = 'https://' + parsed.netloc
		if base_url in known_urls:
			continue
		hosts.append(PluginHost(source, base_url))
		known_urls.add(base_url)
	return tuple(hosts)


class HostSearch:
	"""Cache host results while applying query support each provider offers."""
	def __init__(self, hosts: tuple[PluginHost, ...]) -> None:
		self._hosts = hosts
		self._results = {}
		self._forgejo_results = {}

	def search(self, query: str) -> tuple:
		if query not in self._results:
			results = []
			for host in self._hosts:
				try:
					if host.source == PluginSource.GITLAB:
						repos = gitlab.search(host.base_url, query)
					else:
						repos = self._search_forgejo(host)
					results.extend(self._with_host_hint(repo, host) for repo in repos)
				except (
					HTTPError, URLError, ValueError, KeyError, TypeError, IndexError
				):
					# A single unavailable host must not hide plugins from others.
					continue
			self._results[query] = tuple(results)
		return self._results[query]

	def _search_forgejo(self, host: PluginHost) -> tuple:
		if host.base_url not in self._forgejo_results:
			try:
				self._forgejo_results[host.base_url] = forgejo.search(host.base_url, '')
			except (HTTPError, URLError, ValueError):
				self._forgejo_results[host.base_url] = ()
		return self._forgejo_results[host.base_url]

	@staticmethod
	def _with_host_hint(repo, host: PluginHost):
		label = host.label
		repo.hint = '%s · %d ★' % (label, repo.num_stars) if repo.num_stars else label
		return repo


def repo_for_location(source: PluginSource, location: str):
	if source == PluginSource.GITLAB:
		return gitlab.fetch(location)
	if source == PluginSource.FORGEJO:
		return forgejo.fetch(location)
	raise ValueError('Unsupported plugin source: %s' % source)
