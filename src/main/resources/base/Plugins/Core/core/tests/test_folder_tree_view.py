from core.folder_tree_view import FolderTreeActions, FolderTreeModel, FolderTreeView
from fman.impl.util.qt import CopyAction, MoveAction, get_urls, set_urls
from PyQt5.QtCore import QEvent, QMimeData, Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock, call, patch


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


class FolderTreeViewTest(TestCase):
	def test_open_to_expands_the_target_folder(self):
		actions = FolderTreeActions(Mock(), Mock(), Mock(), Mock())
		with patch.object(FolderTreeModel, 'load') as load:
			view = FolderTreeView(
				True, actions, False, ('#000000', '#ffffff')
			)
			view.show()
			view.open_to(['file:///', 'file:///a'])
			QApplication.processEvents()
			root = view._model.invisibleRootItem()
			root_folder = view._find_child(root, 'file:///')
			target_folder = view._find_child(root_folder, 'file:///a')
			self.assertEqual(
				[call(root_folder), call(target_folder)],
				load.call_args_list
			)

		self.assertTrue(view.isExpanded(root_folder.index()))
		self.assertTrue(view.isExpanded(target_folder.index()))
		self.assertEqual(target_folder.index(), view.currentIndex())

	def test_tab_and_backtab_switch_panes(self):
		switch_panes, close, navigate = Mock(), Mock(), Mock()
		view = FolderTreeView(
			True,
			FolderTreeActions(navigate, close, Mock(), switch_panes),
			False,
			('#000000', '#ffffff')
		)
		for key in (Qt.Key_Tab, Qt.Key_Backtab):
			view.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))

		self.assertEqual(2, switch_panes.call_count)
		close.assert_not_called()
		navigate.assert_not_called()
