"""Send a file drop from outside fman through a pane's file view."""

from dataclasses import dataclass

from fbs_runtime.platform import is_linux, is_mac, is_windows
from fman import fs
from fman.impl.view import FileListView
from PyQt5.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt5.QtWidgets import QApplication


DROP_ACTIONS = frozenset(('copy', 'move', 'default'))
_DROP_RESULT_ACTIONS = {
	Qt.CopyAction: 'copy',
	Qt.MoveAction: 'move',
	Qt.IgnoreAction: 'ignore',
}


class DropTargetMissing(Exception):
	"""Raised when the requested row or empty-area target is unavailable."""


@dataclass(frozen=True)
class DropRequest:
	pane: int
	files: list[str]
	onto: str | None = None
	action: str = 'default'


@dataclass(frozen=True)
class DropResult:
	accepted: bool
	drop_action: str
	dest: str | None


def drop_files(view: FileListView, request: DropRequest) -> DropResult:
	"""Deliver a local file drop to ``view`` using Qt's normal view events."""
	mime_data = QMimeData()
	mime_data.setUrls([QUrl.fromLocalFile(path) for path in request.files])
	return send_drop(view, mime_data, request.onto, request.action)


def send_drop(view: FileListView, mime_data: QMimeData, onto: str | None,
		action: str) -> DropResult:
	"""Send a prepared drag payload through the view's normal drop events."""
	model = view.model()
	viewport = view.viewport()
	if onto is not None:
		index = model.find(onto)
		if not index.isValid() or not fs.is_dir(model.url(index)):
			raise DropTargetMissing(onto)
		point = view.visualRect(index).center()
	else:
		point = _empty_area_point(view, viewport)

	if not viewport.rect().contains(point):
		raise DropTargetMissing('No drop target is visible.')

	modifiers = _drop_modifiers(action)
	possible_actions = Qt.CopyAction | Qt.MoveAction
	buttons = Qt.LeftButton
	enter = QDragEnterEvent(
		point, possible_actions, mime_data, buttons, modifiers)
	move = QDragMoveEvent(
		point, possible_actions, mime_data, buttons, modifiers)
	drop = QDropEvent(
		QPointF(point), possible_actions, mime_data, buttons, modifiers)
	for event in (enter, move, drop):
		QApplication.sendEvent(viewport, event)

	dest = model.drop_dest_url(view.indexAt(point))
	return DropResult(
		drop.isAccepted(),
		_DROP_RESULT_ACTIONS.get(drop.dropAction(), 'ignore'),
		dest,
	)


def _drop_modifiers(action):
	if action == 'copy':
		if is_mac():
			return Qt.AltModifier
		if is_windows() or is_linux():
			return Qt.ControlModifier
	if action == 'move' and is_windows():
		return Qt.ShiftModifier
	return Qt.NoModifier


def _empty_area_point(view, viewport):
	model = view.model()
	visible = [
		view.visualRect(model.index(row, 0))
		for row in range(model.rowCount())
		if view.visualRect(model.index(row, 0)).intersects(viewport.rect())
	]
	if not visible:
		return QPoint(viewport.rect().center().x(), 0)
	last_row = max(visible, key=lambda rect: rect.bottom())
	row_height = max(1, last_row.height())
	return QPoint(last_row.center().x(), last_row.bottom() + row_height)
