"""Pane view for browsing folders as a tree."""
from core.folder_tree import FOLLOW_CURSOR_DELAY_MS
from core.folder_tree_keys import is_tree_key, tree_move_key
from core.key_bindings import command_for_key_event, KEY_BINDINGS_FILE
from fman import load_json
from fman.url import dirname
from fman.impl.util.qt.key_event import QtKeyEvent
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.view.drag_and_drop import DragAndDrop
from PyQt5.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
	QAbstractItemView, QLineEdit, QStyledItemDelegate, QTreeView,
)
from dataclasses import dataclass
from typing import Callable
from fman.impl.util.qt import connect_once
from fman.impl.view import set_selection

from core.folder_tree_model import FolderTreeModel, URL_ROLE

_COMMAND_PALETTE = 'command_palette'


@dataclass
class FolderTreeActions:
	navigate: Callable[[str], None]
	close: Callable[[], None]
	drop: Callable[[list[str], str, bool], None]
	switch_panes: Callable[[], None]
	open_palette: Callable[[], None]
	try_shortcut: Callable[[QKeyEvent], bool] = lambda event: False
	renamed: Callable[[str, str], None] = lambda url, name: None


class _FolderTreeItemDelegate(QStyledItemDelegate):
	editor_shown = pyqtSignal(QLineEdit)

	def __init__(self, actions, parent=None):
		super().__init__(parent)
		self._actions = actions

	def eventFilter(self, editor, event):
		if event.type() == QEvent.Show:
			self.editor_shown.emit(editor)
		return super().eventFilter(editor, event)

	def setModelData(self, editor, model, index):
		new_name = editor.text()
		if new_name and new_name != index.data():
			self._actions.renamed(index.data(URL_ROLE), new_name)

	def destroyEditor(self, editor, index):
		item = index.model().itemFromIndex(index)
		if item is not None:
			item.setEditable(False)
		super().destroyEditor(editor, index)


class FolderTreeView(DragAndDrop, QTreeView):
	def __init__(
		self, show_hidden, actions, follow_cursor, icon_provider, parent=None,
		fs=None
	):
		super().__init__(parent)
		self._actions = actions
		self._fs = fs
		self._follow_cursor = follow_cursor
		self._reveal_url = None
		self._reveal_pending = set()
		self._model = FolderTreeModel(
			show_hidden, actions.drop, icon_provider, self
		)
		self._model.children_loaded.connect(self._on_children_loaded)
		self.setModel(self._model)
		self.setItemDelegate(_FolderTreeItemDelegate(actions, self))
		self.setHeaderHidden(True)
		self.setUniformRowHeights(True)
		self.setRootIsDecorated(True)
		self.expanded.connect(
			lambda index: self._model.load(self._model.itemFromIndex(index))
		)
		self._follow_timer = QTimer(self)
		self._follow_timer.setSingleShot(True)
		self._follow_timer.setInterval(FOLLOW_CURSOR_DELAY_MS)
		self._follow_timer.timeout.connect(self._navigate_current)
		self.selectionModel().currentChanged.connect(self._current_changed)
		if fs is not None:
			self._file_change_callback = self._on_file_changed
			fs.file_added.add_callback(self._file_change_callback)
			fs.file_removed.add_callback(self._file_change_callback)
			self.destroyed.connect(self._unsubscribe)
	def _unsubscribe(self, destroyed_object=None):
		if self._fs is None:
			return
		for event, callback in (
			(self._fs.file_added, self._file_change_callback),
			(self._fs.file_removed, self._file_change_callback),
		):
			try:
				event.remove_callback(callback)
			except (ValueError, FileNotFoundError):
				pass
	@run_in_main_thread
	def _on_file_changed(self, url):
		self._model.refresh(dirname(url))
	def set_font_size(self, size):
		# A local type selector beats the theme's `*` font-size rule; setFont does not.
		self.setStyleSheet(
			'' if size is None else 'FolderTreeView { font-size: %dpt; }' % size
		)
	def _is_command_palette_key(self, key_event, key_bindings):
		return command_for_key_event(
			key_event, key_bindings, [_COMMAND_PALETTE]
		) is not None or key_event.matches('Ctrl+Shift+P')
	def open_to(self, ancestors):
		root = self._model.invisibleRootItem()
		for url in ancestors:
			child = self._find_child(root, url)
			if child is None:
				child = self._model.add_folder(root, url)
			root = child
		self.setCurrentIndex(root.index())
		self._reveal_url = ancestors[-1] if ancestors else None
		self._reveal_pending = set(ancestors)
		self._reveal_current()
		self.setFocus()
		self._expand_to_target(ancestors)
	@run_in_main_thread
	def get_file_under_cursor(self):
		index = self.currentIndex()
		return index.data(URL_ROLE) if index.isValid() else None
	@run_in_main_thread
	def get_selected_files(self):
		return []
	@run_in_main_thread
	def get_location(self):
		index = self.currentIndex()
		if not index.isValid():
			return None
		url = index.data(URL_ROLE)
		if url is None:
			return None
		parent_index = index.parent()
		if not parent_index.isValid():
			return url
		parent = self._model.itemFromIndex(parent_index)
		return parent.data(URL_ROLE) if parent is not None else url
	@run_in_main_thread
	def place_cursor_at(self, url):
		if url is None:
			return
		item = self._find_item(url)
		if item is not None:
			self.setCurrentIndex(item.index())
	def _find_item(self, url):
		if url is None:
			return None
		root = self._model.invisibleRootItem()
		items = [root.child(row) for row in reversed(range(root.rowCount()))]
		while items:
			item = items.pop()
			if item.data(URL_ROLE) == url:
				return item
			items.extend(
				item.child(row)
				for row in reversed(range(item.rowCount()))
			)
		return None
	@run_in_main_thread
	def edit_name(self, url, start=0, end=None):
		item = self._find_item(url)
		if item is None:
			return
		item.setEditable(True)
		delegate = self.itemDelegate()
		connect_once(
			delegate.editor_shown,
			lambda editor: set_selection(editor, start, end)
			)
		self.setCurrentIndex(item.index())
		self.edit(item.index())
	def _reveal_current(self):
		if self._reveal_url and \
				self.currentIndex().data(URL_ROLE) == self._reveal_url:
			self.scrollTo(self.currentIndex(), QAbstractItemView.PositionAtCenter)
	def _on_children_loaded(self, url):
		self._reveal_pending.discard(url)
		# Ancestors load on separate threads and insert rows above the target, so
		# re-center it after each one.
		self._reveal_current()
		if not self._reveal_pending:
			QTimer.singleShot(0, self._finish_reveal)
	def _finish_reveal(self):
		if not self._reveal_pending:
			self._reveal_current()
			self._reveal_url = None
	def _expand_to_target(self, ancestors):
		parent = self._model.invisibleRootItem()
		for url in ancestors:
			item = self._find_child(parent, url)
			if item is None:
				return
			self.expand(item.index())
			parent = item
	def _find_child(self, parent, url):
		for row in range(parent.rowCount()):
			item = parent.child(row)
			if item.data(URL_ROLE) == url:
				return item
	def _current_changed(self, current, previous):
		if self._reveal_url and current.data(URL_ROLE) != self._reveal_url:
			self._reveal_url = None
			self._reveal_pending.clear()
			# shortcut: a manual wheel scroll during loading is undone once more;
			# track scrollbar moves if users notice.
		if self._follow_cursor:
			if current.isValid():
				self._follow_timer.start()
			else:
				self._follow_timer.stop()
	def set_follow_cursor(self, enabled):
		self._follow_cursor = enabled
		if not enabled:
			self._follow_timer.stop()
	def _navigate_current(self):
		index = self.currentIndex()
		url = self._model.data(index, URL_ROLE) if index.isValid() else None
		if url is not None:
			self._actions.navigate(url)
	def keyPressEvent(self, event):
		if self.state() == QAbstractItemView.EditingState and \
				event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
			super().keyPressEvent(event)
			return
		key_event = QtKeyEvent(event.key(), event.modifiers())
		key_bindings = load_json(KEY_BINDINGS_FILE, default=[])
		if self._is_command_palette_key(key_event, key_bindings):
			self._actions.open_palette()
		elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and \
				self.state() != QAbstractItemView.EditingState:
			self._navigate_current()
		elif event.key() == Qt.Key_Escape and \
				self.state() != QAbstractItemView.EditingState:
			self._actions.close()
		elif event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
			self._actions.switch_panes()
		elif is_tree_key(event.key(), event.modifiers()):
			super().keyPressEvent(event)
		else:
			key = tree_move_key(key_event, key_bindings)
			if key is not None:
				super().keyPressEvent(QKeyEvent(
					QEvent.KeyPress, key, Qt.NoModifier
				))
			elif self._actions.try_shortcut(event):
				return
			else:
				super().keyPressEvent(event)
