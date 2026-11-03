from core import LocalFileSystem
from core.commands import navigation
from core.tests.commands import FakePane
from fman import PLATFORM
from fman.fs import Column
from fman.impl.model import SortedFileSystemModel
from fman.url import as_url, splitscheme
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless
from unittest.mock import MagicMock, patch

class _NavigationPane(FakePane):
	def __init__(self, path):
		super().__init__(url=path)
		self.path = path
		self.cursor_url = None
		self.cursor_home = False
	def get_path(self):
		return self.path
	def set_path(self, path, callback=None):
		self.path = path
		if callback:
			callback()
	def place_cursor_at(self, url):
		self.cursor_url = url
	def move_cursor_home(self):
		self.cursor_home = True


@skipUnless(PLATFORM == 'Windows', 'junctions are a Windows concept')
class LinkNavigationTest(TestCase):
	def setUp(self):
		import _winapi

		root = Path(self.enterContext(TemporaryDirectory())).resolve()
		target = root / 'target'
		target.mkdir()
		(target / 'inside.txt').touch()
		link = root / 'link'
		_winapi.CreateJunction(str(target), str(link))
		self.link_url = as_url(str(link))
		self.target_url = as_url(str(target))
		self.root_url = as_url(str(root))

	def test_resolve_follows_the_junction(self):
		path = splitscheme(self.link_url)[1]
		self.assertEqual(self.target_url, LocalFileSystem().resolve(path))

	def test_opening_the_link_keeps_its_path(self):
		fs = MagicMock()
		fs.resolve.side_effect = lambda url: LocalFileSystem().resolve(
			splitscheme(url)[1]
		)
		fs.get_columns.return_value = [Column()]
		with patch.object(
				SortedFileSystemModel, '_set_location_main', autospec=True
		) as set_location_main:
			model = SortedFileSystemModel(None, fs, self.root_url)
			self.addCleanup(model.shutdown)
			model.set_location(self.link_url)
		self.assertEqual(self.link_url, set_location_main.call_args.args[1])

	def test_go_up_from_inside_the_link_returns_next_to_it(self):
		pane = _NavigationPane(self.link_url)
		navigation.go_up(pane)
		self.assertEqual(self.root_url, pane.path)
		self.assertEqual(self.link_url, pane.cursor_url)
		self.assertFalse(pane.cursor_home)
