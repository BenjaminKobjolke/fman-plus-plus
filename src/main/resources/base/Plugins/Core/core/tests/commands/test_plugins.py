from core.commands import plugins as plugins_module
from core.github import GitHubRepo
from unittest import TestCase
from unittest.mock import Mock, patch


def _repo(name='Plugin'):
	return GitHubRepo({
		'name': name, 'full_name': 'someone/' + name, 'default_branch': 'main',
		'description': 'Short summary', 'stargazers_count': 3,
		'url': 'https://api.github.com/repos/someone/' + name
	})


class PickRepoTest(TestCase):
	def setUp(self):
		self.repo = _repo()
		self.command = plugins_module.InstallPlugin(None)
		self.command._plugin_repos = [self.repo]
		patchers = [
			patch.object(plugins_module, 'show_quicksearch'),
			patch.object(plugins_module, 'show_plugin_info'),
			patch.object(plugins_module, 'StatusMessage'),
		]
		self.quicksearch, self.show_info, _ = [p.start() for p in patchers]
		for patcher in patchers:
			self.addCleanup(patcher.stop)

	def test_install_on_info_screen_returns_picked_repo(self):
		self.quicksearch.return_value = ('plug', self.repo)
		self.show_info.return_value = True
		with patch.object(self.repo, 'fetch_description', return_value='# Details'):
			self.assertIs(self.repo, self.command._pick_repo())
		self.show_info.assert_called_once_with('Plugin', '# Details')
		self.quicksearch.assert_called_once_with(
			self.command._get_matching_repos, query=''
		)

	def test_back_reopens_picker_with_previous_query(self):
		self.quicksearch.side_effect = [('plug', self.repo), ('plugin', self.repo)]
		self.show_info.side_effect = [False, True]
		with patch.object(self.repo, 'fetch_description', return_value='# Details'):
			self.assertIs(self.repo, self.command._pick_repo())
		self.assertEqual(2, self.quicksearch.call_count)
		self.assertEqual('', self.quicksearch.call_args_list[0].kwargs['query'])
		self.assertEqual('plug', self.quicksearch.call_args_list[1].kwargs['query'])

	def test_picker_cancel_does_not_show_info_screen(self):
		self.quicksearch.return_value = None
		self.assertIsNone(self.command._pick_repo())
		self.show_info.assert_not_called()

	def test_missing_description_uses_fallback_markdown(self):
		self.quicksearch.return_value = ('', self.repo)
		self.show_info.return_value = True
		with patch.object(self.repo, 'fetch_description', return_value=None):
			self.command._pick_repo()
		markdown = self.show_info.call_args.args[1]
		self.assertIn('# Plugin', markdown)
		self.assertIn('Short summary', markdown)
		self.assertIn('No description available', markdown)

	@patch('core.commands.plugins._get_thirdparty_plugins', return_value=[])
	def test_install_search_orders_hosts_and_deduplicates(self, _):
		command = plugins_module.InstallPlugin(None)
		command._plugin_repos = [self.repo]
		command._host_search = MockSearch((
			_host_repo('HostPlugin', 'GitLab · 3 ★'),
			_host_repo('Plugin', 'Codeberg · 2 ★'),
		))
		command._catalog_results[''] = (
			_host_repo('CatalogPlugin', 'fman catalog'),
			_host_repo('HostPlugin', 'Duplicate catalog'),
		)

		items = list(command._get_matching_repos(''))

		self.assertEqual(['Plugin', 'HostPlugin', 'CatalogPlugin'], [
			item.title for item in items
		])
		self.assertEqual('GitLab · 3 ★', items[1].hint)

	@patch('core.commands.plugins.show_alert')
	@patch('core.commands.plugins.load_installed_plugin', return_value=True)
	@patch('core.commands.plugins.record_installation')
	@patch('core.commands.plugins.install_zip', return_value='/plugins/Host')
	@patch('core.commands.plugins.StatusMessage')
	def test_install_records_other_host_source_and_location(
			self, status, install_zip, record_installation,
			load_installed_plugin, show_alert):
		repo = _host_repo('Host', 'GitLab · 3 ★', source='gitlab')
		repo.get_latest_release = Mock(return_value='v1')
		repo.download_zipball = Mock(return_value=b'zip')
		command = plugins_module.InstallPlugin(None)
		command._pick_repo = Mock(return_value=repo)

		command()

		record_installation.assert_called_once_with(
			'/plugins/Host', 'https://gitlab.example/team/Host', 'v1',
			source='gitlab'
		)


def _host_repo(name, hint, source='forgejo'):
	repo = Mock()
	repo.name = name
	repo.description = name
	repo.num_stars = 3
	repo.hint = hint
	repo.source = source
	repo.location = 'https://gitlab.example/team/' + name
	return repo


class MockSearch:
	def __init__(self, repos):
		self.repos = repos

	def search(self, query):
		return self.repos
