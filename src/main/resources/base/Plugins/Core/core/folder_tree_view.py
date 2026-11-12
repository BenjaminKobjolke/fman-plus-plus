"""Qt model and pane view for browsing folders as a tree."""
from core.folder_tree import FOLLOW_CURSOR_DELAY_MS, can_drop, list_subfolders
from fman.impl.util.qt import FMAN_URLS_MIME, MoveAction, CopyAction, \
	IgnoreAction, get_urls, set_urls
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.view.drag_and_drop import DragAndDrop
from PyQt5.QtCore import QMimeData, QPersistentModelIndex, QModelIndex, Qt, QTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QFileIconProvider, QTreeView
from dataclasses import dataclass
from threading import Thread
from typing import Callable, Optional

import sip

URL_ROLE = Qt.UserRole + 1


@dataclass
class FolderTreeActions:
	navigate: Callable[[str], None]
	close: Callable[[], None]
	drop: Callable[[list[str], str, bool], None]
	switch_panes: Callable[[], None]


class FolderTreeModel(QStandardItemModel):
	def __init__(self, show_hidden, drop_callback, parent=None):
		super().__init__(parent)
		self._show_hidden = show_hidden
		self._drop_callback = drop_callback
		self._loading = set()
		self._loaded = set()
		self._icons = QFileIconProvider()
		self.setColumnCount(1)
	def add_folder(self, parent, url):
		item = QStandardItem(
			self._icons.icon(QFileIconProvider.Folder),
			url.rsplit('/', 1)[-1] or '/'
		)
		item.setEditable(False)
		item.setData(url, URL_ROLE)
		item.appendRow(QStandardItem())
		parent.appendRow(item)
		return item
	def load(self, item):
		url = item.data(URL_ROLE)
		if url in self._loading or url in self._loaded:
			return
		self._loading.add(url)
		persistent = QPersistentModelIndex(item.index())
		def work():
			children = list_subfolders(url, self._show_hidden)
			@run_in_main_thread
			def apply():
				self._loading.discard(url)
				self._loaded.add(url)
				if not persistent.isValid():
					return
				parent_item = self.itemFromIndex(QModelIndex(persistent))
				if parent_item is None:
					return
				existing = {
					parent_item.child(row).data(URL_ROLE): parent_item.child(row)
					for row in range(parent_item.rowCount())
					if parent_item.child(row).data(URL_ROLE)
				}
				child_urls = set(children)
				for row in reversed(range(parent_item.rowCount())):
					child = parent_item.child(row)
					if child.data(URL_ROLE) not in child_urls:
						parent_item.removeRow(row)
				for child in children:
					folder = existing.get(child)
					if folder is None:
						self.add_folder(parent_item, child)
					else:
						parent_item.appendRow(folder)
			apply()
		Thread(target=work, daemon=True).start()
	def mimeTypes(self):
		return ['text/uri-list', FMAN_URLS_MIME]
	def mimeData(self, indexes):
		data = QMimeData()
		urls = [
			self.data(index, URL_ROLE)
			for index in indexes if index.column() == 0
		]
		set_urls(data, urls)
		sip.transferto(data, None)
		return data
	def supportedDropActions(self):
		return MoveAction | CopyAction | IgnoreAction
	def drop_dest_url(self, index: QModelIndex) -> Optional[str]:
		return self.data(index, URL_ROLE) if index.isValid() else None
	def canDropMimeData(self, data, action, row, column, parent):
		if action == IgnoreAction:
			return True
		if not data.hasUrls() or not parent.isValid():
			return False
		return can_drop(get_urls(data), self.data(parent, URL_ROLE))
	def dropMimeData(self, data, action, row, column, parent):
		if action == IgnoreAction:
			return True
		urls = get_urls(data)
		if not self.canDropMimeData(data, action, row, column, parent):
			return False
		self._drop_callback(urls, self.data(parent, URL_ROLE), action == CopyAction)
		return True


class FolderTreeView(DragAndDrop, QTreeView):
	def __init__(self, show_hidden, actions, follow_cursor, colors, parent=None):
		super().__init__(parent)
		self._actions = actions
		self._follow_cursor = follow_cursor
		self._model = FolderTreeModel(show_hidden, actions.drop, self)
		self.setModel(self._model)
		self.setHeaderHidden(True)
		self.setUniformRowHeights(True)
		self.setRootIsDecorated(True)
		bg, fg = colors
		self.setStyleSheet(
			'QTreeView { color: %s; background-color: %s; }' % (fg, bg)
		)
		self.expanded.connect(
			lambda index: self._model.load(self._model.itemFromIndex(index))
		)
		self._follow_timer = QTimer(self)
		self._follow_timer.setSingleShot(True)
		self._follow_timer.setInterval(FOLLOW_CURSOR_DELAY_MS)
		self._follow_timer.timeout.connect(self._navigate_current)
		self.selectionModel().currentChanged.connect(self._current_changed)
	def open_to(self, ancestors):
		root = self._model.invisibleRootItem()
		for url in ancestors:
			child = self._find_child(root, url)
			if child is None:
				child = self._model.add_folder(root, url)
			root = child
		self.setCurrentIndex(root.index())
		self.scrollTo(root.index())
		self.setFocus()
		self._expand_to_target(ancestors)
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
		if self._follow_cursor:
			self._follow_timer.start()
	def set_follow_cursor(self, enabled):
		self._follow_cursor = enabled
		if not enabled:
			self._follow_timer.stop()
	def _navigate_current(self):
		index = self.currentIndex()
		if index.isValid():
			self._actions.navigate(self._model.data(index, URL_ROLE))
	def keyPressEvent(self, event):
		if event.key() in (Qt.Key_Return, Qt.Key_Enter):
			self._navigate_current()
		elif event.key() == Qt.Key_Escape:
			self._actions.close()
		elif event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
			self._actions.switch_panes()
		else:
			super().keyPressEvent(event)
