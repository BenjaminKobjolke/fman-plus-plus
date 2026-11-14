"""Read-only text and font-size readouts for fman's in-window dialogs."""

from PyQt5.QtWidgets import QAbstractItemView, QLabel, QLineEdit


def _point_size(widget):
	if widget is None or widget.isHidden():
		return None
	widget.ensurePolished()
	return widget.font().pointSizeF()


def quicksearch_details(dialog):
	header = dialog.findChild(QLabel, 'header')
	footer = dialog.findChild(QLabel, 'footer')
	query = dialog.focusProxy()
	return {
		'type': type(dialog).__name__,
		'title': header.text() if header and header.isVisible() else '',
		'text': footer.text() if footer else '',
		'value': query.text(),
		'buttons': [],
		'font_sizes': {
			'title': _point_size(header),
			'value': _point_size(query),
			'footer': _point_size(footer),
		},
	}


def prompt_font_sizes(prompt):
	return {
		'title': _point_size(prompt.findChild(QLabel, 'header')),
		'value': _point_size(prompt.focusProxy()),
		'detail': _point_size(prompt.findChild(QLabel, 'detail')),
	}


def rename_editor_details(window):
	for view in window.findChildren(QAbstractItemView):
		if view.state() != QAbstractItemView.EditingState:
			continue
		editor = next((editor for editor in
			view.viewport().findChildren(QLineEdit) if editor.isVisible()), None)
		if editor is None:
			continue
		return {
			'type': 'RenameEditor',
			'title': '',
			'text': str(view.model().data(view.currentIndex())),
			'value': editor.text(),
			'buttons': [],
			'font_sizes': {'value': _point_size(editor)},
		}
	return None
