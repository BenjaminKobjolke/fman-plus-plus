from core.folder_tree import can_drop, list_subfolders, tree_ancestors
from unittest import TestCase
from unittest.mock import patch


class TreeAncestorsTest(TestCase):
	def test_local_url_has_root_first(self):
		self.assertEqual(
			['file:///', 'file:///a', 'file:///a/b', 'file:///a/b/c'],
			tree_ancestors('file:///a/b/c'),
		)
	def test_zip_url_stops_at_archive_root(self):
		self.assertEqual(
			['zip:///', 'zip:///archive.zip', 'zip:///archive.zip/folder',
			 'zip:///archive.zip/folder/subfolder'],
			tree_ancestors('zip:///archive.zip/folder/subfolder'),
		)
	def test_root_url_has_no_repeated_ancestor(self):
		self.assertEqual(['file:///'], tree_ancestors('file:///'))


class ListSubfoldersTest(TestCase):
	def test_lists_only_folders_in_case_insensitive_order(self):
		entries = ['zulu', 'beta.txt', 'Alpha', 'charlie']
		with patch('core.folder_tree.fs.iterdir', return_value=entries), \
			patch('core.folder_tree.fs.is_dir',
			      side_effect=lambda url: not url.endswith('.txt')):
			self.assertEqual(
				['file:///parent/Alpha', 'file:///parent/charlie',
				 'file:///parent/zulu'],
				list_subfolders('file:///parent', show_hidden=True),
			)
	def test_filters_hidden_folders(self):
		entries = ['.hidden', 'visible']
		with patch('core.folder_tree.fs.iterdir', return_value=entries), \
			patch('core.folder_tree.fs.is_dir', return_value=True), \
			patch('core.folder_tree._is_hidden_file',
			      side_effect=lambda url: url.endswith('.hidden')):
			self.assertEqual(
				['file:///parent/visible'],
				list_subfolders('file:///parent', show_hidden=False),
			)
	def test_skips_entries_that_disappear_or_cannot_be_read(self):
		entries = ['missing', 'denied', 'error', 'folder']
		def is_dir(url):
			if url.endswith('missing'):
				raise FileNotFoundError()
			if url.endswith('denied'):
				raise PermissionError()
			if url.endswith('error'):
				raise OSError()
			return True
		with patch('core.folder_tree.fs.iterdir', return_value=entries), \
			patch('core.folder_tree.fs.is_dir', side_effect=is_dir):
			self.assertEqual(
				['file:///parent/folder'],
				list_subfolders('file:///parent', show_hidden=True),
			)
	def test_returns_empty_when_directory_cannot_be_listed(self):
		with patch('core.folder_tree.fs.iterdir', side_effect=PermissionError()), \
			patch('core.folder_tree.fs.is_dir') as is_dir:
			self.assertEqual([], list_subfolders('file:///parent', show_hidden=True))
		is_dir.assert_not_called()


class CanDropTest(TestCase):
	def test_refuses_when_all_files_are_already_in_destination(self):
		self.assertFalse(can_drop(
			['file:///dest/one.txt', 'file:///dest/two.txt'], 'file:///dest'
		))
	def test_refuses_drop_into_a_dragged_folder_or_its_descendant(self):
		self.assertFalse(can_drop(['file:///source'], 'file:///source'))
		self.assertFalse(can_drop(['file:///source'], 'file:///source/child'))
	def test_accepts_other_drops(self):
		self.assertTrue(can_drop(['file:///source/item.txt'], 'file:///dest'))
		self.assertTrue(can_drop(['zip:///archive/item.txt'], 'file:///dest'))
