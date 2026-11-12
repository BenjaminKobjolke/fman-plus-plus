"""Qt model and pane view for browsing folders as a tree."""
from core.folder_tree import FOLLOW_CURSOR_DELAY_MS, can_drop, list_subfolders
from core.key_bindings import command_for_key_event, KEY_BINDINGS_FILE
from fman import load_json
from fman.url import dirname
from fman.impl.util.qt import FMAN_URLS_MIME, MoveAction, CopyAction, \
	IgnoreAction, get_urls, set_urls
from fman.impl.util.qt.key_event import QtKeyEvent
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.view.drag_and_drop import DragAndDrop
from PyQt5.QtCore import (
	QMimeData, QPersistentModelIndex, QModelIndex, Qt, QTimer, pyqtSignal,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAbstractItemView, QFileIconProvider, QTreeView
from dataclasses import dataclass
from threading import Thread
from typing import Callable, Optional

import sip

URL_ROLE = Qt.UserRole + 1
_COMMAND_PALETTE = 'command_palette'


@dataclass
class FolderTreeActions:
	navigate: Callable[[str], None]
	close: Callable[[], None]
	drop: Callable[[list[str], str, bool], None]
	switch_panes: Callable[[], None]
	open_palette: Callable[[], None]


class FolderTreeModel(QStandardItemModel):
	children_loaded = pyqtSignal(str)

	def __init__(self, show_hidden, drop_callback, icon_provider, parent=None):
		super().__init__(parent)
		self._show_hidden = show_hidden
		self._drop_callback = drop_callback
		self._loading = set()
		self._loaded = set()
		self._pending_refresh = set()
		self._icon_provider = icon_provider
		self._fallback_icon = QFileIconProvider().icon(
			QFileIconProvider.Folder
		)
		self.setColumnCount(1)
	def add_folder(self, parent, url, row=None):
		try:
			icon = self._icon_provider.get_icon(url)
		except OSError:
			icon = self._fallback_icon
		item = QStandardItem(
			icon,
			url.rsplit('/', 1)[-1] or '/'
		)
		item.setEditable(False)
		item.setData(url, URL_ROLE)
		item.appendRow(QStandardItem())
		if row is None:
			parent.appendRow(item)
		else:
			parent.insertRow(row, item)
		return item
	def load(self, item):
		url = item.data(URL_ROLE)
		if url in self._loading or url in self._loaded:
			return
		self._loading.add(url)
		persistent = QPersistentModelIndex(item.index())
		def work():
			try:
				children = list_subfolders(url, self._show_hidden)
			except Exception:
				children = []
			@run_in_main_thread
			def apply():
				self._loading.discard(url)
				self._loaded.add(url)
				if not persistent.isValid():
					self._pending_refresh.discard(url)
					return
				parent_item = self.itemFromIndex(QModelIndex(persistent))
				if parent_item is None:
					return
				child_urls = set(children)
				for row in reversed(range(parent_item.rowCount())):
					child = parent_item.child(row)
					if child.data(URL_ROLE) not in child_urls:
						parent_item.removeRow(row)
				# Keep existing rows in place so the current index and expanded subtree
				# survive.
				for row, child in enumerate(children):
					if row < parent_item.rowCount() and \
							parent_item.child(row).data(URL_ROLE) == child:
						continue
					# shortcut: Existing rows are sorted already; an out-of-order one
					# stays put.
					self.add_folder(parent_item, child, row)
				self.children_loaded.emit(url)
				if url in self._pending_refresh:
					self._pending_refresh.discard(url)
					self._loaded.discard(url)
					self.load(parent_item)
			apply()
		Thread(target=work, daemon=True).start()
	def refresh(self, url):
		if url in self._loading:
			self._pending_refresh.add(url)
			return
		if url not in self._loaded:
			return
		root = self.invisibleRootItem()
		items = [root.child(row) for row in reversed(range(root.rowCount()))]
		while items:
			item = items.pop()
			if item.data(URL_ROLE) == url:
				self._loaded.discard(url)
				self.load(item)
				return
			items.extend(
				item.child(row)
				for row in reversed(range(item.rowCount()))
			)
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
	def _is_command_palette_key(self, event):
		key_event = QtKeyEvent(event.key(), event.modifiers())
		key_bindings = load_json(KEY_BINDINGS_FILE, default=[])
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
		root = self._model.invisibleRootItem()
		items = [root.child(row) for row in reversed(range(root.rowCount()))]
		while items:
			item = items.pop()
			if item.data(URL_ROLE) == url:
				self.setCurrentIndex(item.index())
				return
			items.extend(
				item.child(row)
				for row in reversed(range(item.rowCount()))
			)
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
		if self._is_command_palette_key(event):
			self._actions.open_palette()
		elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
			self._navigate_current()
		elif event.key() == Qt.Key_Escape:
			self._actions.close()
		elif event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
			self._actions.switch_panes()
		else:
			super().keyPressEvent(event)
