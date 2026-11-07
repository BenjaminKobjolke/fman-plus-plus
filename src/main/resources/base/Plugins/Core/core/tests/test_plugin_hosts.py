from core.plugin_hosts import HostSearch, configured_hosts, repo_for_location
from core.plugin_list import PluginSource
from unittest import TestCase
from unittest.mock import patch
from urllib.error import URLError


class PluginHostsTest(TestCase):
	def test_defaults_and_valid_configured_hosts(self):
		with patch('core.plugin_hosts.get_setting', return_value=[
			{'type': 'gitlab', 'url': 'https://git.example.com/'},
			{'type': 'forgejo', 'url': 'http://bad.example'},
			{'type': 'unknown', 'url': 'https://unknown.example'},
			{'type': 'gitlab', 'url': 'https://gitlab.com/'},
		]):
			hosts = configured_hosts()
		self.assertEqual(
			['https://gitlab.com', 'https://codeberg.org', 'https://git.example.com'],
			[host.base_url for host in hosts]
		)
		self.assertEqual(['GitLab', 'Codeberg', 'git.example.com'], [
			host.label for host in hosts
		])

	def test_search_caches_results_and_skips_unavailable_host(self):
		from core.plugin_hosts import PluginHost
		hosts = (PluginHost(PluginSource.GITLAB, 'https://gitlab.com'),)
		search = HostSearch(hosts)
		with patch(
			'core.plugin_hosts.gitlab.search', side_effect=URLError('offline')
		) as call:
			self.assertEqual((), search.search('term'))
			self.assertEqual((), search.search('term'))
		self.assertEqual(1, call.call_count)

	def test_search_skips_malformed_host_response_and_continues(self):
		from core.plugin_hosts import PluginHost
		hosts = (
			PluginHost(PluginSource.GITLAB, 'https://gitlab.com'),
			PluginHost(PluginSource.FORGEJO, 'https://codeberg.org'),
		)
		search = HostSearch(hosts)
		repo = type('Repo', (), {'num_stars': 1})()
		with patch(
			'core.plugin_hosts.gitlab.search', side_effect=KeyError('web_url')
		):
			with patch(
				'core.plugin_hosts.forgejo.search', return_value=(repo,)
			):
				results = search.search('term')
		self.assertEqual((repo,), results)
		self.assertEqual('Codeberg · 1 ★', repo.hint)

	def test_search_caches_gitlab_per_query_and_forgejo_per_host(self):
		from core.plugin_hosts import PluginHost
		hosts = (
			PluginHost(PluginSource.GITLAB, 'https://gitlab.com'),
			PluginHost(PluginSource.FORGEJO, 'https://codeberg.org'),
		)
		search = HostSearch(hosts)
		gitlab_repo = type('Repo', (), {'num_stars': 2})()
		forgejo_repo = type('Repo', (), {'num_stars': 1})()
		with patch(
			'core.plugin_hosts.gitlab.search', return_value=(gitlab_repo,)
		) as gitlab_call:
			with patch(
				'core.plugin_hosts.forgejo.search', return_value=(forgejo_repo,)
			) as forgejo_call:
				first = search.search('one')
				self.assertEqual(first, search.search('one'))
				second = search.search('two')
		self.assertEqual(2, gitlab_call.call_count)
		self.assertEqual(1, forgejo_call.call_count)
		self.assertEqual('GitLab · 2 ★', first[0].hint)
		self.assertEqual('Codeberg · 1 ★', first[1].hint)
		self.assertEqual(first[1], second[1])

	def test_location_dispatches_by_source(self):
		with patch(
			'core.plugin_hosts.gitlab.fetch', return_value='gitlab'
	) as gitlab_fetch:
			self.assertEqual(
				'gitlab', repo_for_location(
					PluginSource.GITLAB, 'https://gitlab.com/group/plugin'
				)
			)
		gitlab_fetch.assert_called_once()
		with patch('core.plugin_hosts.forgejo.fetch', return_value='forgejo'):
			self.assertEqual(
				'forgejo', repo_for_location(
					PluginSource.FORGEJO, 'https://codeberg.org/team/plugin'
				)
			)
