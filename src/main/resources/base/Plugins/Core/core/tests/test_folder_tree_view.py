from core.folder_tree_view import FolderTreeModel
from fman.impl.util.qt import CopyAction, MoveAction, get_urls, set_urls
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock


_app = QApplication.instance() or QApplication([])


class FolderTreeModelTest(TestCase):
	def test_drag_urls_and_drop_to_folder(self):
		drop = Mock()
		model = FolderTreeModel(True, drop)
		root = model.invisibleRootItem()
		folder = model.add_folder(root, 'file:///dest')
		mime = model.mimeData([folder.index()])
		self.assertEqual(['file:///dest'], get_urls(mime))
		incoming = QMimeData()
		set_urls(incoming, ['file:///source/file.txt'])
		self.assertTrue(model.canDropMimeData(
			incoming, MoveAction, -1, 0, folder.index()
		))
		self.assertTrue(model.dropMimeData(
			incoming, CopyAction, -1, 0, folder.index()
		))
		drop.assert_called_once_with(
			['file:///source/file.txt'], 'file:///dest', True
		)
	def test_rejects_drop_into_a_dragged_folder(self):
		model = FolderTreeModel(True, Mock())
		folder = model.add_folder(model.invisibleRootItem(), 'file:///source')
		incoming = QMimeData()
		set_urls(incoming, ['file:///source'])
		self.assertFalse(model.canDropMimeData(
			incoming, MoveAction, -1, 0, folder.index()
		))
