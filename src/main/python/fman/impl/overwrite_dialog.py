"""The overwrite prompt uses a QDialog because QMessageBox only has one button row."""
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, \
	QPushButton, QVBoxLayout


EXISTING_LABEL = 'Existing'
INCOMING_LABEL = 'Incoming'
SIZE_LABEL = 'Size'
MODIFIED_LABEL = 'Modified'
VERSION_LABEL = 'Version'
NEWER_MARK = ' (newer)'
LARGER_MARK = ' (larger)'
BUTTON_LABELS = {
	'OVERWRITE': '&Overwrite',
	'OVERWRITE_ALL': 'Overwrite &all',
	'RENAME': '&Rename',
	'RENAME_ALL': 'Rena&me all',
	'SKIP': '&Skip',
	'SKIP_ALL': 'S&kip all',
	'ABORT': 'A&bort',
}


class OverwriteChoice(Enum):
	OVERWRITE = 'overwrite'
	OVERWRITE_ALL = 'overwrite_all'
	RENAME = 'rename'
	RENAME_ALL = 'rename_all'
	SKIP = 'skip'
	SKIP_ALL = 'skip_all'
	ABORT = 'abort'


@dataclass(frozen=True)
class FileDetails:
	size: str
	modified: str
	version: str = ''
	is_larger: bool = False
	is_newer: bool = False


class OverwriteDialog(QDialog):
	def __init__(self, parent, text, details):
		super().__init__(parent)
		self.choice = OverwriteChoice.ABORT
		self.buttons = {}
		self.button_rows = []
		self.setWindowTitle('File already exists')

		layout = QVBoxLayout(self)
		message = QLabel(str(text), self)
		message.setWordWrap(True)
		layout.addWidget(message)
		if details is not None:
			self._add_details(layout, details)

		for choices in (
			(
				OverwriteChoice.OVERWRITE,
				OverwriteChoice.OVERWRITE_ALL,
				OverwriteChoice.RENAME,
				OverwriteChoice.RENAME_ALL,
			),
			(
				OverwriteChoice.SKIP,
				OverwriteChoice.SKIP_ALL,
				OverwriteChoice.ABORT,
			),
		):
			row = QHBoxLayout()
			self.button_rows.append(row)
			for choice in choices:
				button = QPushButton(BUTTON_LABELS[choice.name], self)
				button.setObjectName(choice.name.lower())
				button.clicked.connect(
					lambda _checked=False, selected=choice: self._choose(selected)
				)
				self.buttons[choice] = button
				row.addWidget(button)
			layout.addLayout(row)

		self.buttons[OverwriteChoice.OVERWRITE].setDefault(True)
		self.buttons[OverwriteChoice.OVERWRITE].setFocus(Qt.OtherFocusReason)

	def _add_details(self, layout, details):
		existing, incoming = details
		grid = QGridLayout()
		grid.addWidget(QLabel(''), 0, 0)
		grid.addWidget(QLabel(EXISTING_LABEL), 0, 1)
		grid.addWidget(QLabel(INCOMING_LABEL), 0, 2)
		rows = (
			(SIZE_LABEL, 'size', LARGER_MARK, 'is_larger'),
			(MODIFIED_LABEL, 'modified', NEWER_MARK, 'is_newer'),
		)
		if existing.version or incoming.version:
			rows += ((VERSION_LABEL, 'version', '', ''),)
		for row_index, (label, attribute, mark, mark_attribute) in enumerate(
			rows, start=1
		):
			grid.addWidget(QLabel(label), row_index, 0)
			for column, detail in enumerate((existing, incoming), start=1):
				value = getattr(detail, attribute)
				if mark_attribute and getattr(detail, mark_attribute):
					value += mark
				grid.addWidget(QLabel(value), row_index, column)
		layout.addLayout(grid)

	def _choose(self, choice):
		self.choice = choice
		self.accept()

	def reject(self):
		self.choice = OverwriteChoice.ABORT
		super().reject()
