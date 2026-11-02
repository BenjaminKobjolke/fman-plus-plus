from tempfile import TemporaryDirectory
from unittest import TestCase
from os.path import join

from fman.impl.quicksearch_width import QuicksearchWidth
from fman.impl.util.settings import Settings


class QuicksearchWidthTest(TestCase):
	def setUp(self):
		self.directory = TemporaryDirectory()
		self.path = join(self.directory.name, 'Settings.json')
		self.settings = Settings(self.path)
		self.width = QuicksearchWidth(self.settings)

	def tearDown(self):
		self.directory.cleanup()

	def test_get_returns_none_when_width_has_never_been_saved(self):
		self.assertIsNone(self.width.get())

	def test_save_remembers_a_non_default_width(self):
		self.width.save(900, 600)
		self.assertEqual(900, self.width.get())
		self.assertEqual(900, QuicksearchWidth(Settings(self.path)).get())

	def test_save_default_width_removes_the_setting(self):
		self.width.save(900, 600)
		self.width.save(600, 600)
		self.assertIsNone(self.width.get())

	def test_save_width_below_default_removes_the_setting(self):
		self.width.save(900, 600)
		self.width.save(500, 600)
		self.assertIsNone(self.width.get())
