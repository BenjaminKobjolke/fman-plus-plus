"""Lazy-loading model for the folder tree."""
from core.folder_tree import can_drop, list_subfolders
from fman.impl.util.qt import (
	FMAN_URLS_MIME, MoveAction, CopyAction, IgnoreAction, get_urls, set_urls,
)
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtCore import QMimeData, QPersistentModelIndex, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QFileIconProvider
from concurrent.futures import Future
from threading import Condition, Event, Lock, Thread
from typing import Optional
import sip

URL_ROLE = Qt.UserRole + 1
_ICON_WORKERS = 2


class _IconExecutor:
	"""Run shell icon lookups on a fixed number of daemon workers."""

	def __init__(self, max_workers):
		self._condition = Condition()
		self._pending = []
		for index in range(max_workers):
			Thread(
				target=self._work, name='folder-tree-icons-%d' % index,
				daemon=True
			).start()
	def submit(self, fn, *args):
		future = Future()
		with self._condition:
			self._pending.append((future, fn, args))
			self._condition.notify()
		return future
	def cancel(self, future):
		with self._condition:
			for task in self._pending:
				if task[0] is future:
					self._pending.remove(task)
					future.cancel()
					return
		future.cancel()
	def _work(self):
		while True:
			with self._condition:
				while not self._pending:
					self._condition.wait()
				future, fn, args = self._pending.pop(0)
			if not future.set_running_or_notify_cancel():
				continue
			try:
				result = fn(*args)
			except BaseException as error:
				future.set_exception(error)
			else:
				future.set_result(result)


_ICON_EXECUTOR = _IconExecutor(_ICON_WORKERS)


class FolderTreeModel(QStandardItemModel):
	children_loaded = pyqtSignal(str)

	def __init__(self, show_hidden, drop_callback, icon_provider, parent=None):
		super().__init__(parent)
		self._show_hidden = show_hidden
		self._drop_callback = drop_callback
		self._loading = set()
		self._loaded = set()
		self._pending_refresh = set()
		self._stopped = Event()
		self._icon_futures = set()
		self._icon_futures_lock = Lock()
		self._icon_provider = icon_provider
		self._fallback_icon = QFileIconProvider().icon(
			QFileIconProvider.Folder
		)
		self.setColumnCount(1)
	def stop(self) -> None:
		"""End background loads of a closed tree.

		Their shell icon lookups would otherwise keep running next to a new
		tree's and starve the GUI thread.
		"""
		self._stopped.set()
		with self._icon_futures_lock:
			futures = list(self._icon_futures)
		for future in futures:
			_ICON_EXECUTOR.cancel(future)
	def add_folder(self, parent, url, row=None, icon=None):
		if icon is None:
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
	def _icon_for(self, url):
		try:
			return self._icon_provider.get_icon(url)
		except OSError:
			return self._fallback_icon
	def load(self, item):
		url = item.data(URL_ROLE)
		if url in self._loading or url in self._loaded:
			return
		self._loading.add(url)
		persistent = QPersistentModelIndex(item.index())
		stopped = self._stopped
		def work():
			try:
				children = list_subfolders(url, self._show_hidden)
			except Exception:
				children = []
			if stopped.is_set():
				return
			@run_in_main_thread
			def apply_rows():
				if stopped.is_set():
					return
				if not persistent.isValid():
					self._loading.discard(url)
					return
				parent_item = self.itemFromIndex(QModelIndex(persistent))
				if parent_item is None:
					self._loading.discard(url)
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
					self.add_folder(
						parent_item, child, row
					)
				self.children_loaded.emit(url)
				future = _ICON_EXECUTOR.submit(
					self._load_icons, url, children, persistent, stopped
				)
				with self._icon_futures_lock:
					self._icon_futures.add(future)
				future.add_done_callback(self._forget_icon_future)
			apply_rows()
		Thread(target=work, daemon=True).start()
	def _forget_icon_future(self, future):
		with self._icon_futures_lock:
			self._icon_futures.discard(future)
	def _load_icons(self, url, children, persistent, stopped):
		icons = {}
		for child in children:
			if stopped.is_set():
				return
			icons[child] = self._icon_for(child)
			if len(icons) == 32:
				self._apply_icons(persistent, icons)
				icons = {}
		if stopped.is_set():
			return
		own_icon = self._icon_for(url)
		if icons or own_icon is not None:
			icons[url] = own_icon
			self._apply_icons(persistent, icons)
		if stopped.is_set():
			return
		@run_in_main_thread
		def finish():
			self._loading.discard(url)
			self._loaded.add(url)
			if not persistent.isValid():
				self._pending_refresh.discard(url)
				return
			parent_item = self.itemFromIndex(QModelIndex(persistent))
			if parent_item is None:
				return
			if url in self._pending_refresh:
				self._pending_refresh.discard(url)
				self._loaded.discard(url)
				self.load(parent_item)
		finish()
	def _apply_icons(self, persistent, icons):
		@run_in_main_thread
		def apply():
			if self._stopped.is_set() or not persistent.isValid():
				return
			parent = self.itemFromIndex(QModelIndex(persistent))
			if parent is None:
				return
			if parent.data(URL_ROLE) in icons:
				parent.setIcon(icons[parent.data(URL_ROLE)])
			for row in range(parent.rowCount()):
				child = parent.child(row)
				url = child.data(URL_ROLE)
				if url in icons:
					child.setIcon(icons[url])
		apply()
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


