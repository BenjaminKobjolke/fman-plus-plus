"""Time directory enumeration, metadata, shell icons, and table painting.

Columns separate os.listdir, os.stat, lazy QFileIconProvider.icon, its first
and second pixmap(16) passes, ShellIconProvider fetch, and average QTableView
grab time for lazy versus materialized icons. The first run after boot measures
the cold shell cache. Run in a Windows desktop session, not offscreen:
    uv run python tools/profile_directory_phases.py <dir> [<dir> ...]
"""

from fman.impl.model.shell_icons import ShellIconProvider
from pathlib import Path
from PyQt5.QtCore import QFileInfo, QSize
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QFileIconProvider, QTableView
from statistics import mean
from time import perf_counter
import os
import sys


def _milliseconds(operation):
	start = perf_counter()
	result = operation()
	return result, (perf_counter() - start) * 1000


def _paint_average(icons, names):
	model = QStandardItemModel()
	for icon, name in zip(icons, names):
		item = QStandardItem(name)
		item.setIcon(icon)
		model.appendRow(item)
	view = QTableView()
	view.setModel(model)
	view.setIconSize(QSize(16, 16))
	view.verticalHeader().hide()
	view.horizontalHeader().hide()
	view.resize(900, 900)
	view.show()
	QApplication.processEvents()
	times = []
	for _ in range(5):
		start = perf_counter()
		view.grab()
		times.append((perf_counter() - start) * 1000)
	view.close()
	return mean(times)


def _profile(directory):
	names, listdir_ms = _milliseconds(lambda: os.listdir(directory))
	paths = [os.path.join(directory, name) for name in names]
	_, stat_ms = _milliseconds(lambda: [os.stat(path) for path in paths])
	infos = [QFileInfo(path) for path in paths]
	qt_provider = QFileIconProvider()
	lazy_icons, lazy_fetch_ms = _milliseconds(
		lambda: [qt_provider.icon(info) for info in infos]
	)
	_, first_pixmap_ms = _milliseconds(
		lambda: [icon.pixmap(QSize(16, 16)) for icon in lazy_icons]
	)
	_, second_pixmap_ms = _milliseconds(
		lambda: [icon.pixmap(QSize(16, 16)) for icon in lazy_icons]
	)
	shell_provider = ShellIconProvider()
	shell_icons, shell_fetch_ms = _milliseconds(
		lambda: [shell_provider.icon(info) for info in infos]
	)
	for lazy_icon, shell_icon in zip(lazy_icons, shell_icons):
		assert lazy_icon.pixmap(QSize(16, 16)).toImage() == \
			shell_icon.pixmap(QSize(16, 16)).toImage()
	lazy_paint_ms = _paint_average(lazy_icons, names)
	shell_paint_ms = _paint_average(shell_icons, names)
	return (
		len(names), listdir_ms, stat_ms, lazy_fetch_ms, first_pixmap_ms,
		second_pixmap_ms, shell_fetch_ms, lazy_paint_ms, shell_paint_ms
	)


def main():
	if len(sys.argv) < 2:
		raise SystemExit(__doc__)
	if sys.platform != 'win32':
		raise SystemExit('This profile requires Windows shell icons.')
	app = QApplication.instance() or QApplication([])
	print(
		'directory | entries | listdir ms | stat all ms | lazy icon ms | '
		'first pixmap ms | second pixmap ms | shell fetch ms | '
		'lazy paint avg ms | materialized paint avg ms'
	)
	for value in sys.argv[1:]:
		directory = str(Path(value).expanduser())
		if not os.path.isdir(directory):
			raise SystemExit('Not a directory: %s' % value)
		print('%s | %s' % (directory, ' | '.join(
			'%.2f' % item if isinstance(item, float) else str(item)
			for item in _profile(directory)
		)))
	app.processEvents()


if __name__ == '__main__':
	main()
