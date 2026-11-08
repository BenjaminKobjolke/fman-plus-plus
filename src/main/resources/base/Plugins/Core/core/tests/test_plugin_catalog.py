from core.plugin_catalog import CatalogPlugin, search
from core.commands.plugins import InstallPlugin
from core.fman_api import FmanApiClient
from core.plugin_hosts import HostSearch
from unittest import TestCase
from types import SimpleNamespace
from unittest.mock import Mock, patch


class CatalogPluginTest(TestCase):
	def test_plugin_adapts_catalog_releases_and_downloads(self):
		client = Mock(spec=FmanApiClient)
		client.get_catalog_releases.return_value = (
			SimpleNamespace(version='2.0'), SimpleNamespace(version='1.0')
		)
		client.download_release.return_value = b'zip bytes'
		client.catalog_plugin_url.return_value = 'https://example.test/api/v1/plugins/Example'
		plugin = CatalogPlugin(client, 'Example', 'Example description')

		self.assertEqual('Example', plugin.name)
		self.assertEqual('Example description', plugin.description)
		self.assertEqual(0, plugin.num_stars)
		self.assertEqual('https://example.test/api/v1/plugins/Example', plugin.url)
		self.assertEqual('Example description', plugin.fetch_description())
		self.assertEqual('2.0', plugin.get_latest_release())
		self.assertEqual(b'zip bytes', plugin.download_zipball('2.0'))
		client.get_catalog_releases.assert_called_once_with('Example')
		client.download_release.assert_called_once_with('Example', '2.0')
		client.catalog_plugin_url.assert_called_once_with('Example')

	def test_search_wraps_each_api_result(self):
		client = Mock(spec=FmanApiClient)
		client.search_catalog.return_value = [
			SimpleNamespace(name='Example', description='Example description')
		]

		plugins = search(client, 'exa')

		client.search_catalog.assert_called_once_with('exa', limit=20)
		self.assertEqual('Example', plugins[0].name)
		self.assertEqual('Example description', plugins[0].description)

	@patch('core.commands.plugins._get_thirdparty_plugins', return_value=[])
	def test_install_search_lists_github_before_catalog_and_deduplicates(self, _):
		command = InstallPlugin(None)
		command._plugin_repos = [SimpleNamespace(
			name='GitHubPlugin', description='GitHub', num_stars=3
		)]
		command._host_search = Mock(spec=HostSearch)
		command._host_search.search.return_value = ()
		command._catalog_results[''] = (
			CatalogPlugin(Mock(spec=FmanApiClient), 'CatalogPlugin', 'Catalog'),
			CatalogPlugin(Mock(spec=FmanApiClient), 'GitHubPlugin', 'Duplicate')
		)

		items = list(command._get_matching_repos(''))

		self.assertEqual(
			['GitHubPlugin', 'CatalogPlugin'], [item.title for item in items]
		)
		self.assertEqual('fman catalog', items[1].hint)

	@patch('core.commands.plugins.show_alert')
	@patch('core.commands.plugins.load_installed_plugin', return_value=True)
	@patch('core.commands.plugins.record_installation')
	@patch('core.commands.plugins.install_zip', return_value='/plugins/Example')
	@patch('core.commands.plugins.StatusMessage')
	def test_install_records_catalog_source_and_location(
			self, status, install_zip, record_installation,
			load_installed_plugin, show_alert):
		client = Mock(spec=FmanApiClient)
		client.get_catalog_releases.return_value = [SimpleNamespace(version='2.0')]
		client.download_release.return_value = b'zip bytes'
		plugin = CatalogPlugin(client, 'Example', 'Catalog plugin')
		command = InstallPlugin(None)
		command._plugin_repos = []
		command._pick_repo = Mock(spec=InstallPlugin._pick_repo,
			return_value=plugin)

		command()

		install_zip.assert_called_once_with('Example', b'zip bytes')
		record_installation.assert_called_once_with(
			'/plugins/Example', 'Example', '2.0', source='catalog'
		)
		load_installed_plugin.assert_called_once_with('/plugins/Example', None)

	@patch('core.commands.plugins.search_catalog', return_value=())
	def test_catalog_search_is_cached_per_distinct_query(self, search_catalog):
		command = InstallPlugin(None)
		command._catalog_client = Mock(spec=FmanApiClient)

		command._get_catalog_plugins('one')
		command._get_catalog_plugins('one')
		command._get_catalog_plugins('two')

		self.assertEqual(2, search_catalog.call_count)
