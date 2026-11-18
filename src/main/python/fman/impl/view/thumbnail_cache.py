"""Load and retain thumbnails without doing image work on the GUI thread."""

from collections import OrderedDict
from threading import Lock
from typing import Iterable
import weakref

from fman.impl.view.shell_thumbnails import shell_thumbnail
from fman.impl.view.thumbnail_loader import load_image_thumbnail
from fman.impl.view.thumbnail_settings import ThumbnailSettings
from fman.url import as_human_readable
from PyQt5.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap


class _ThumbnailSignals(QObject):
	loaded = pyqtSignal(int, str, int, object)


class _ThumbnailTask(QRunnable):
	def __init__(self, cache, generation, url, size, kind):
		super().__init__()
		self._cache = weakref.ref(cache)
		self._generation = generation
		self._url = url
		self._size = size
		self._kind = kind

	def run(self):
		cache = self._cache()
		if cache is None or not cache._is_current(self._generation):
			return
		if self._kind == 'shell':
			image = shell_thumbnail(
				as_human_readable(self._url), self._size
			)
		else:
			image = load_image_thumbnail(self._url, self._size)
		cache = self._cache()
		if cache is not None:
			cache._signals.loaded.emit(
				self._generation, self._url, self._size, image
			)


class ThumbnailCache(QObject):
	"""Asynchronously load previews and expose them as GUI-thread pixmaps."""

	ready = pyqtSignal(str)

	def __init__(self, settings: ThumbnailSettings, max_entries: int = 400,
			parent: QObject | None = None) -> None:
		super().__init__(parent)
		if max_entries < 1:
			raise ValueError('max_entries must be positive')
		self._settings = settings
		self._max_entries = max_entries
		self._entries: OrderedDict[tuple[str, int], QPixmap | None] = \
			OrderedDict()
		self._pending: set[tuple[int, str, int]] = set()
		self._generation = 0
		self._priority = 0
		self._generation_lock = Lock()
		self._pool = QThreadPool(self)
		self._pool.setMaxThreadCount(2)
		self._signals = _ThumbnailSignals(self)
		self._signals.loaded.connect(
			self._on_loaded, Qt.QueuedConnection
		)

	def get(self, url: str) -> QPixmap | None:
		key = (url, self._settings.size)
		if key not in self._entries:
			return None
		self._entries.move_to_end(key)
		return self._entries[key]

	def request(self, urls: Iterable[str]) -> None:
		generation = self._generation
		for url in reversed(list(urls)):
			kind = self._settings.wants_preview(url)
			if kind is None:
				continue
			key = (url, self._settings.size)
			pending_key = (generation, url, self._settings.size)
			if key in self._entries or pending_key in self._pending:
				continue
			self._pending.add(pending_key)
			self._priority += 1
			self._pool.start(_ThumbnailTask(
				self, generation, url, self._settings.size, kind,
			), self._priority)

	def clear(self) -> None:
		with self._generation_lock:
			self._generation += 1
		self._entries.clear()
		self._pending.clear()

	def set_settings(self, settings: ThumbnailSettings) -> None:
		if settings != self._settings:
			self._settings = settings
			self.clear()

	def _is_current(self, generation: int) -> bool:
		with self._generation_lock:
			return generation == self._generation

	def _on_loaded(self, generation: int, url: str, size: int,
			image: QImage | None) -> None:
		key = (url, size)
		self._pending.discard((generation, url, size))
		if generation != self._generation or size != self._settings.size:
			return
		pixmap = QPixmap.fromImage(image) if image is not None else None
		self._entries[key] = pixmap
		self._entries.move_to_end(key)
		while len(self._entries) > self._max_entries:
			self._entries.popitem(last=False)
		self.ready.emit(url)
