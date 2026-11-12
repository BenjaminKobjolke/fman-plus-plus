"""Lazy-loading model for the folder tree."""
from core.folder_tree import can_drop, list_subfolders
from fman.impl.util.qt import (
	FMAN_URLS_MIME, MoveAction, CopyAction, IgnoreAction, get_urls, set_urls,
)
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtCore import QMimeData, QPersistentModelIndex, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QFileIconProvider
from threading import Thread
from typing import Optional
import sip

URL_ROLE = Qt.UserRole + 1


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


