from core.file_mention_index import FileMentionIndex
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import os

class FileMentionIndexTest(TestCase):
	def setUp(self):
		self._tmp = TemporaryDirectory()
		self.root = self._tmp.name
		# a/ is listed before z.md, so a depth-first walk would put a/deep/
		# entries ahead of z.md; level by level must not.
		for rel_dir in ('a/deep/deeper', 'b', '.git/objects'):
			os.makedirs(join(self.root, *rel_dir.split('/')))
		for rel_file in ('z.md', 'a/one.md', 'a/deep/two.md', '.git/HEAD'):
			with open(join(self.root, *rel_file.split('/')), 'w'):
				pass
	def tearDown(self):
		self._tmp.cleanup()
	def test_lists_each_level_before_the_next(self):
		depths = [
			entry.rel_path.count(os.sep)
			for entry in self._walk(frozenset({'.git'}))
		]
		self.assertEqual(sorted(depths), depths)
	def test_does_not_enter_excluded_folders(self):
		rel_paths = {e.rel_path for e in self._walk(frozenset({'.git'}))}
		self.assertNotIn('.git', rel_paths)
		self.assertNotIn(join('.git', 'HEAD'), rel_paths)
		self.assertIn(join('a', 'deep', 'two.md'), rel_paths)
	def test_marks_folders(self):
		entries = {e.rel_path: e for e in self._walk(frozenset())}
		self.assertTrue(entries['a'].is_dir)
		self.assertFalse(entries['z.md'].is_dir)
		self.assertEqual(join(self.root, 'z.md'), entries['z.md'].path)
	def test_stop_ends_the_walk(self):
		index = FileMentionIndex(self.root, frozenset())
		index.stop()
		index._run()
		self.assertEqual([], index.snapshot())
		self.assertTrue(index.done)
	def test_refreshes_when_the_walk_ends(self):
		index = FileMentionIndex(self.root, frozenset())
		calls = []
		index.set_refresh(lambda: calls.append(1))
		self.assertFalse(index.done)
		index._run()
		self.assertTrue(index.done)
		self.assertTrue(calls)
	def test_stops_at_the_entry_cap(self):
		with patch('core.file_mention_index.MAX_ENTRIES', 2):
			self.assertEqual(2, len(self._walk(frozenset())))
	def _walk(self, excluded):
		index = FileMentionIndex(self.root, excluded)
		index._run()
		return index.snapshot()
