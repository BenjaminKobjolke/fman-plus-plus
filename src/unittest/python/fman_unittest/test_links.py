import unittest

from fman import links


class LinksTest(unittest.TestCase):
	def test_url_constants_use_https_and_do_not_point_to_upstream(self):
		url_constants = [
			value
			for name, value in vars(links).items()
			if name.isupper() and isinstance(value, str) and name != 'GITHUB_REPO'
		]

		for url in url_constants:
			with self.subTest(url=url):
				self.assertTrue(url.startswith('https://'))
				self.assertNotIn('fman.io', url)

	def test_issues_points_to_the_fork(self):
		self.assertTrue(links.ISSUES.endswith('BenjaminKobjolke/fman/issues'))

	def test_changelog_uses_github_releases(self):
		self.assertEqual(links.RELEASES, links.CHANGELOG)
