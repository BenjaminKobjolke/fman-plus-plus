from core.folder_tree_view import (
	FolderTreeActions, FolderTreeModel, FolderTreeView, URL_ROLE,
)
from fman.impl.util.qt import CopyAction, MoveAction, get_urls, set_urls
from PyQt5.QtCore import QEvent, QMimeData, Qt
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock, call, patch


_app = QApplication.instance() or QApplication([])


def _icon_provider():
	provider = Mock()
	provider.get_icon.return_value = QIcon()
	return provider


class SynchronousThread:
	def __init__(self, target, daemon):
		self._target = target
	def start(self):
		self._target()


class FolderTreeModelTest(TestCase):
	def load_children(self, model, parent, children):
		with patch('core.folder_tree_view.Thread', SynchronousThread), \
				patch('core.folder_tree_view.list_subfolders', return_value=children):
			model.load(parent)

	def test_load_inserts_children_in_order_around_an_existing_child(self):
		model = FolderTreeModel(True, Mock(), _icon_provider())
		parent = model.add_folder(model.invisibleRootItem(), 'file:///p')
		existing_child = model.add_folder(parent, 'file:///p/b')

		self.load_children(
			model, parent,
			['file:///p/a', 'file:///p/b', 'file:///p/c']
		)

		self.assertEqual(3, parent.rowCount())
		self.assertEqual(
			['file:///p/a', 'file:///p/b', 'file:///p/c'],
			[parent.child(row).data(URL_ROLE)
			 for row in range(parent.rowCount())]
		)
		self.assertIs(existing_child, parent.child(1))

	def test_load_keeps_the_loaded_subtree_of_an_existing_child(self):
		model = FolderTreeModel(True, Mock(), _icon_provider())
		parent = model.add_folder(model.invisibleRootItem(), 'file:///p')
		existing_child = model.add_folder(parent, 'file:///p/b')
		grandchild = model.add_folder(existing_child, 'file:///p/b/c')

		self.load_children(model, parent, ['file:///p/a', 'file:///p/b'])

		self.assertIn(
			grandchild,
			[existing_child.child(row) for row in range(existing_child.rowCount())]
		)
	def test_load_clears_placeholder_when_listing_raises(self):
		model = FolderTreeModel(True, Mock(), _icon_provider())
		parent = model.add_folder(model.invisibleRootItem(), 'file:///p')

		with patch('core.folder_tree_view.Thread', SynchronousThread), \
			patch('core.folder_tree_view.list_subfolders', side_effect=RuntimeError):
			model.load(parent)

		self.assertEqual(0, parent.rowCount())
		self.assertNotIn('file:///p', model._loading)
		self.assertIn('file:///p', model._loaded)
	def test_add_folder_uses_injected_icon_provider(self):
		icons = Mock()
		icons.get_icon.return_value = QIcon()
		model = FolderTreeModel(True, Mock(), icons)

		model.add_folder(model.invisibleRootItem(), 'file:///p')

		icons.get_icon.assert_called_once_with('file:///p')

	def test_drag_urls_and_drop_to_folder(self):
		drop = Mock()
		model = FolderTreeModel(True, drop, _icon_provider())
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
		model = FolderTreeModel(True, Mock(), _icon_provider())
		folder = model.add_folder(model.invisibleRootItem(), 'file:///source')
		incoming = QMimeData()
		set_urls(incoming, ['file:///source'])
		self.assertFalse(model.canDropMimeData(
			incoming, MoveAction, -1, 0, folder.index()
		))


class FolderTreeViewTest(TestCase):
	def test_open_to_keeps_the_target_visible_after_parents_load(self):
		children = ['file:///f%02d' % i for i in range(60)] + ['file:///m']
		def list_children(url, show_hidden):
			return children if url == 'file:///' else []
		actions = FolderTreeActions(Mock(), Mock(), Mock(), Mock(), Mock())
		with patch('core.folder_tree_view.Thread', SynchronousThread), \
				patch(
					'core.folder_tree_view.list_subfolders',
					side_effect=list_children
				):
			view = FolderTreeView(
				True, actions, False, _icon_provider()
			)
			view.resize(300, 200)
			view.show()
			view.open_to(['file:///', 'file:///m'])
			QApplication.processEvents()

		self.assertTrue(
			view.viewport().rect().intersects(view.visualRect(view.currentIndex()))
		)
		self.assertEqual('file:///m', view.currentIndex().data(URL_ROLE))

	def test_open_to_expands_the_target_folder(self):
		actions = FolderTreeActions(Mock(), Mock(), Mock(), Mock(), Mock())
		with patch.object(FolderTreeModel, 'load') as load:
			view = FolderTreeView(
				True, actions, False, _icon_provider()
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
			FolderTreeActions(navigate, close, Mock(), switch_panes, Mock()),
			False, _icon_provider()
		)
		for key in (Qt.Key_Tab, Qt.Key_Backtab):
			view.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier))

		self.assertEqual(2, switch_panes.call_count)
		close.assert_not_called()
		navigate.assert_not_called()
	def test_navigation_ignores_placeholder_row(self):
		navigate = Mock()
		view = FolderTreeView(
			True, FolderTreeActions(navigate, Mock(), Mock(), Mock(), Mock()),
			False, _icon_provider()
		)
		parent = view._model.add_folder(
			view._model.invisibleRootItem(), 'file:///p'
		)
		view.setCurrentIndex(parent.child(0).index())

		view._navigate_current()

		navigate.assert_not_called()
	def test_command_palette_key_opens_palette(self):
		open_palette = Mock()
		actions = FolderTreeActions(
			Mock(), Mock(), Mock(), Mock(), open_palette
		)
		view = FolderTreeView(
			True, actions, False, _icon_provider()
		)
		with patch('core.folder_tree_view.load_json', return_value=[{
			'keys': ['Ctrl+Shift+P'], 'command': 'command_palette'
		}]):
			view.keyPressEvent(QKeyEvent(
				QEvent.KeyPress, Qt.Key_P,
				Qt.ControlModifier | Qt.ShiftModifier
			))

		open_palette.assert_called_once_with()
