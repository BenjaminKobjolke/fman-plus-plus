from core import forgejo
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError


class ForgejoTest(TestCase):
	def test_search_queries_fman_topic_and_filters_plugin_topic(self):
		with patch.object(forgejo, '_get_json', return_value={'data': [
			_repo(), _repo(name='Other', topics=['fman'])
		]}) as get:
			repos = forgejo.search('https://codeberg.org', '')
		self.assertEqual(
			'https://codeberg.org/api/v1/repos/search?q=fman&topic=true'
			'&archived=false&sort=updated&order=desc&limit=50',
			get.call_args.args[0]
		)
		self.assertEqual(['plugin'], [repo.name for repo in repos])
		self.assertEqual('https://codeberg.org/team/plugin', repos[0].location)

	def test_release_commit_archive_and_description(self):
		repo = forgejo.ForgejoRepo('https://codeberg.org', _repo())
		with patch.object(forgejo, '_get_json', side_effect=[
			{'tag_name': 'v1'}, [{'sha': 'abc'}]
		]) as get:
			self.assertEqual('v1', repo.get_latest_release())
			self.assertEqual('abc', repo.get_latest_commit())
		self.assertIn(
			'/repos/team/plugin/releases/latest', get.call_args_list[0].args[0]
		)
		with patch.object(forgejo, '_get', return_value=b'zip') as get_bytes:
			self.assertEqual(b'zip', repo.download_zipball('v1'))
		self.assertEqual(
			'https://codeberg.org/api/v1/repos/team/plugin/archive/v1.zip',
			get_bytes.call_args.args[0]
		)
		with patch.object(forgejo, '_get', return_value=b'# Info') as get_bytes:
			self.assertEqual('# Info', repo.fetch_description())
		self.assertIn('/raw/description.md?ref=main', get_bytes.call_args.args[0])

	def test_missing_release_and_optional_description_are_handled(self):
		repo = forgejo.ForgejoRepo('https://codeberg.org', _repo())
		missing = HTTPError('url', 404, 'Not Found', {}, None)
		with patch.object(forgejo, '_get_json', side_effect=missing):
			with self.assertRaises(LookupError):
				repo.get_latest_release()
		for error in (missing, URLError('offline')):
			with patch.object(forgejo, '_get', side_effect=error):
				self.assertIsNone(repo.fetch_description())
		with patch.object(forgejo, '_get', return_value=b'\xff'):
			self.assertIsNone(repo.fetch_description())

	def test_fetch_uses_repository_path_and_requires_https(self):
		with patch.object(forgejo, '_get_json', return_value=_repo()) as get:
			forgejo.fetch('https://codeberg.org/team/plugin')
		self.assertEqual(
			'https://codeberg.org/api/v1/repos/team/plugin',
			get.call_args.args[0]
		)
		with self.assertRaises(ValueError):
			forgejo.fetch('http://codeberg.org/team/plugin')


def _repo(name='plugin', topics=None):
	return {
		'name': name, 'owner': {'login': 'team'}, 'description': 'A plugin',
		'stars_count': 5, 'html_url': 'https://codeberg.org/team/' + name,
		'default_branch': 'main', 'topics': topics or ['fman', 'plugin']
	}
