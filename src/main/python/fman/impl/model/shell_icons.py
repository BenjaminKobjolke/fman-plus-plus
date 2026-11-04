"""Materialize lazy Windows shell icons before the view paints them.

Qt's Windows icons are lazy and call the shell on the GUI thread at paint time.
"""

from PyQt5.QtCore import QFileInfo, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileIconProvider
from threading import Lock

_SPECIAL_SUFFIXES = {'EXE', 'LNK', 'ICO'}


class ShellIconProvider:
	_SIZES = (16, 32, 48)
	# shortcut: 64 px (the maximum icon size) is drawn from the 48 px pixmap
	# upscaled; add a size if that looks soft.

	def __init__(self) -> None:
		self._provider = QFileIconProvider()
		self._cache: dict[tuple[str, str], QIcon] = {}
		self._lock = Lock()

	def icon(self, file_info: QFileInfo) -> QIcon:
		key = self._cache_key(file_info)
		with self._lock:
			if key is not None and key in self._cache:
				return self._cache[key]
			result = QIcon()
			lazy = self._provider.icon(file_info)
			for size in self._SIZES:
				result.addPixmap(lazy.pixmap(QSize(size, size)))
			if key is not None:
				self._cache[key] = result
			return result

	@staticmethod
	def _cache_key(file_info: QFileInfo) -> tuple[str, str] | None:
		if file_info.isDir():
			return None
		suffix = file_info.suffix().upper()
		if suffix in _SPECIAL_SUFFIXES:
			return None
		if suffix:
			return ('suffix', suffix)
		return ('name', file_info.fileName())
