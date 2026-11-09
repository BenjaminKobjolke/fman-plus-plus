"""Multiline text input displayed in a frameless prompt dialog."""

from fman.impl.frameless_dialog import make_frameless, text_width_floor
from fman.impl.util.qt import NoFocus
from fman.localization import translate
from fman.localization_keys import (
	PROMPT_CANCEL, PROMPT_OK, QUICKSEARCH_KEY_ENTER,
	QUICKSEARCH_KEY_SHIFT_ENTER, TEXT_INPUT_NEW_LINE, TEXT_INPUT_SAVE,
)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
	QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QStyle, QVBoxLayout,
)


class TextInputPrompt(QDialog):
	def __init__(self, parent, message='', default=''):
		super().__init__(parent, Qt.FramelessWindowHint)
		make_frameless(self)
		self.setWindowTitle(message)
		title, _, detail = message.partition('\n')
		layout = QVBoxLayout(self)
		layout.setContentsMargins(*(
			self.style().pixelMetric(metric, None, self)
			for metric in (
				QStyle.PM_LayoutLeftMargin, QStyle.PM_LayoutTopMargin,
				QStyle.PM_LayoutRightMargin, QStyle.PM_LayoutBottomMargin,
			)
		))
		self._header = QLabel(title, self)
		self._header.setObjectName('header')
		layout.addWidget(self._header)
		if detail:
			self._detail = QLabel(detail, self)
			self._detail.setObjectName('detail')
			layout.addWidget(self._detail)
		self._text = _TextEditor(self)
		self._text.setObjectName('text')
		self._text.setPlainText(str(default))
		self._text.setMinimumWidth(text_width_floor(self))
		self._text.selectAll()
		layout.addWidget(self._text)
		self._footer = QLabel(self._footer_text(), self)
		self._footer.setObjectName('footer')
		layout.addWidget(self._footer)
		self._buttons = QDialogButtonBox(
			QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self
		)
		self._buttons.setObjectName('buttons')
		self._buttons.button(QDialogButtonBox.Ok).setText(translate(PROMPT_OK))
		self._buttons.button(QDialogButtonBox.Cancel).setText(
			translate(PROMPT_CANCEL)
		)
		for button in self._buttons.buttons():
			button.setFocusPolicy(NoFocus)
			button.setAutoDefault(False)
			button.setDefault(False)
		self._buttons.accepted.connect(self.accept)
		self._buttons.rejected.connect(self.reject)
		layout.addSpacing(
			self.style().pixelMetric(QStyle.PM_LayoutVerticalSpacing, None, self)
		)
		layout.addWidget(self._buttons)
		layout.setSizeConstraint(layout.SetFixedSize)
		self._text.setFocus()
	def _footer_text(self):
		return '%s  %s    %s  %s' % (
			translate(QUICKSEARCH_KEY_ENTER), translate(TEXT_INPUT_SAVE),
			translate(QUICKSEARCH_KEY_SHIFT_ENTER),
			translate(TEXT_INPUT_NEW_LINE),
		)
	def textValue(self):
		return self._text.toPlainText()


class _TextEditor(QPlainTextEdit):
	def __init__(self, dialog):
		super().__init__(dialog)
		self._dialog = dialog
	def keyPressEvent(self, event):
		if event.key() in (Qt.Key_Return, Qt.Key_Enter):
			if event.modifiers() & Qt.ShiftModifier:
				super().keyPressEvent(event)
			else:
				self._dialog.accept()
		elif event.key() == Qt.Key_Escape:
			self._dialog.reject()
		else:
			super().keyPressEvent(event)
