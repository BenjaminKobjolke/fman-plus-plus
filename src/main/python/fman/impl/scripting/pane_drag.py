"""Replay a file-list drag between two fman panes through Qt drop events."""

from dataclasses import dataclass

from PyQt5.QtCore import QMimeData

from fman.impl.scripting.automation import UnknownFile
from fman.impl.scripting.external_drop import (
	DROP_ACTIONS, DropResult, DropTargetMissing, send_drop,
)
from fman.impl.util.qt import set_urls


@dataclass(frozen=True)
class PaneDragRequest:
	source_pane: int
	files: list[str]
	pane: int
	onto: str | None = None
	action: str = 'default'


def parse_pane_drag(payload):
	source_pane = payload.get('source_pane', 0)
	pane = payload.get('pane', 1)
	files = payload.get('files')
	onto = payload.get('onto')
	action = payload.get('action', 'default')
	if any(not isinstance(value, int) or isinstance(value, bool)
		for value in (source_pane, pane)):
		raise ValueError('source_pane and pane must be integers.')
	if not isinstance(files, list) or not files or any(
		not isinstance(file, str) or not file for file in files
	):
		raise ValueError('files must be a non-empty list of URLs.')
	if onto is not None and not isinstance(onto, str):
		raise ValueError('onto must be a string.')
	if not isinstance(action, str) or action not in DROP_ACTIONS:
		raise ValueError('action must be copy, move or default.')
	return PaneDragRequest(source_pane, files, pane, onto, action)


def drag_between(source_view, target_view,
		request: PaneDragRequest) -> DropResult:
	model = source_view.model()
	for url in request.files:
		try:
			index = model.find(url)
		except (ValueError, KeyError):
			raise UnknownFile(url) from None
		if not index.isValid():
			raise UnknownFile(url)
	mime_data = QMimeData()
	set_urls(mime_data, request.files)
	return send_drop(target_view, mime_data, request.onto, request.action)
