from core import gitlab
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError, URLError


class GitLabTest(TestCase):
	def test_search_builds_topic_and_query_url_and_maps_projects(self):
		project = _project()
		with patch.object(gitlab, '_get_json', return_value=[project]) as get:
			repos = gitlab.search('https://gitlab.com', 'a plugin')
		self.assertEqual(
			'https://gitlab.com/api/v4/projects?topic=fman%2Cplugin&search=a+plugin'
			'&archived=false&order_by=last_activity_at&sort=desc&per_page=20',
			get.call_args.args[0]
		)
		self.assertEqual('group/plugin', repos[0].name)
		self.assertEqual('https://gitlab.com/group/plugin', repos[0].location)
		self.assertEqual(3, repos[0].num_stars)

	def test_release_commit_archive_and_description(self):
		repo = gitlab.GitLabProject('https://gitlab.com', _project())
		with patch.object(gitlab, '_get_json', side_effect=[
			{'tag_name': 'v1'}, [{'id': 'abc'}]
		]) as get:
			self.assertEqual('v1', repo.get_latest_release())
			self.assertEqual('abc', repo.get_latest_commit())
		self.assertIn(
			'/projects/17/releases/permalink/latest', get.call_args_list[0].args[0]
		)
		with patch.object(gitlab, '_get', return_value=b'zip') as get_bytes:
			self.assertEqual(b'zip', repo.download_zipball('v1'))
		self.assertEqual(
			'https://gitlab.com/api/v4/projects/17/repository/archive.zip?sha=v1',
			get_bytes.call_args.args[0]
		)
		with patch.object(gitlab, '_get', return_value=b'# Info') as get_bytes:
			self.assertEqual('# Info', repo.fetch_description())
		self.assertIn(
			'/repository/files/description.md/raw?ref=main',
			get_bytes.call_args.args[0]
		)

	def test_missing_release_and_optional_description_are_handled(self):
		repo = gitlab.GitLabProject('https://gitlab.com', _project())
		missing = HTTPError('url', 404, 'Not Found', {}, None)
		with patch.object(gitlab, '_get_json', side_effect=missing):
			with self.assertRaises(LookupError):
				repo.get_latest_release()
		for error in (missing, URLError('offline')):
			with patch.object(gitlab, '_get', side_effect=error):
				self.assertIsNone(repo.fetch_description())
		with patch.object(gitlab, '_get', return_value=b'\xff'):
			self.assertIsNone(repo.fetch_description())

	def test_fetch_uses_encoded_project_path_and_requires_https(self):
		with patch.object(gitlab, '_get_json', return_value=_project()) as get:
			gitlab.fetch('https://gitlab.com/a/b/plugin')
		self.assertEqual(
			'https://gitlab.com/api/v4/projects/a%2Fb%2Fplugin',
			get.call_args.args[0]
		)
		with self.assertRaises(ValueError):
			gitlab.fetch('http://gitlab.com/a/plugin')


def _project():
	return {
		'id': 17, 'path': 'group/plugin', 'description': 'A plugin',
		'star_count': 3, 'web_url': 'https://gitlab.com/group/plugin',
		'default_branch': 'main'
	}
