"""Destination prompt displayed with the Quicksearch popup."""

from fman import QuicksearchItem
from fman.impl.prompt_completion import PromptTabCompletion
from fman.impl.prompt_suggestions import PromptSuggestions
from fman.impl.frameless_dialog import make_frameless, text_width_floor
from fman.impl.quicksearch import Quicksearch
from fman.impl.util.qt import Key_Down, Key_Up, NoFocus
from fman.localization import translate
from fman.localization_keys import PROMPT_CANCEL, PROMPT_OK
from PyQt5.QtWidgets import (
	QDialog, QDialogButtonBox, QLabel, QLineEdit, QStyle, QStyleOptionFrame
)


# The title sits one step above the input and the path one step below.
_TITLE_STEP_PTS = 2
# Qt's fixed QLineEditPrivate::horizontalMargin.
_LINE_EDIT_HORIZONTAL_MARGIN = 2


class Prompt(Quicksearch):
	def _outer_margins(self):
		make_frameless(self)
		return tuple(self.style().pixelMetric(metric, None, self) for metric in (
			QStyle.PM_LayoutLeftMargin, QStyle.PM_LayoutTopMargin,
			QStyle.PM_LayoutRightMargin, QStyle.PM_LayoutBottomMargin
		))
	def _list_min_width(self):
		return text_width_floor(self)
	def __init__(
		self, parent, app, css, message='', default='', selection_start=0,
		selection_end=None, get_completions=None, password=False,
		width_store=None
	):
		self._message = message
		title, _, detail = message.partition('\n')
		super().__init__(
			parent, app, css, lambda _query: [], query=default,
			width_store=width_store, title=title
		)
		self._detail = None
		if detail:
			self._detail = QLabel(detail, self)
			self._detail.setObjectName('detail')
			self.layout().insertWidget(1, self._detail)
		self.layout().activate()
		self._apply_text_hierarchy()
		self._selection_start = selection_start
		self._selection_end = selection_end
		self._request_immediate_repaint = False
		self._is_second_paint = False
		self._setting_suggestion = False
		self._query.setEchoMode(
			QLineEdit.Password if password else QLineEdit.Normal
		)
		self._prompt_tab_completion = None
		self._suggestions = None
		if get_completions is not None:
			self._prompt_tab_completion = PromptTabCompletion(
				self._query, get_completions
			)
			self._suggestions = PromptSuggestions(
				get_completions, self._set_suggestions, self
			)
			self.finished.connect(self._suggestions.close)
			self._suggestions.request(default)
		self._items.setCurrentIndex(self._items.model().index(-1, 0))
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
		self._buttons.accepted.connect(self._on_return_pressed)
		self._buttons.rejected.connect(self.reject)
		self.layout().addSpacing(
			self.style().pixelMetric(QStyle.PM_LayoutVerticalSpacing, None, self)
		)
		self.layout().addWidget(self._buttons)
		self._adjust_item_list_ize()
	def _apply_text_hierarchy(self):
		self._query.ensurePolished()
		pts = self._query.font().pointSizeF()
		option = QStyleOptionFrame()
		self._query.initStyleOption(option)
		contents = self._query.style().subElementRect(
			QStyle.SE_LineEditContents, option, self._query
		)
		text_left = (
			self._query.mapTo(self, contents.topLeft()).x()
			+ self._query.textMargins().left()
			+ _LINE_EDIT_HORIZONTAL_MARGIN
		)
		# Platform and theme styles change the input inset, so match it directly.
		def style_label(label, point_size):
			# QSS padding shifts both contentsRect() and QLabel's draw area.
			# Move those insets to the widget margins so text moves only once.
			contents = label.contentsRect()
			right = label.width() - contents.right() - 1
			bottom = label.height() - contents.bottom() - 1
			label.setStyleSheet(
				'font-size: %gpt; padding: 0px;' % point_size
			)
			label.setContentsMargins(
				text_left - label.geometry().x(), contents.top(), right, bottom
			)
		style_label(self._header, pts + _TITLE_STEP_PTS)
		if self._detail is not None:
			style_label(self._detail, max(1, pts - _TITLE_STEP_PTS))
	def setTextValue(self, text):
		self._query.setText(text)
	def textValue(self):
		return self._query.text()
	def is_password(self):
		return self._query.echoMode() == QLineEdit.Password
	def labelText(self):
		return self._message
	def setVisible(self, visible):
		if visible:
			self._query.end(False)
			self._request_immediate_repaint = True
		QDialog.setVisible(self, visible)
		if visible:
			self._apply_text_hierarchy()
	def paintEvent(self, event):
		if self._request_immediate_repaint:
			self._request_immediate_repaint = False
			self.update()
			self._is_second_paint = True
		elif self._is_second_paint:
			self._is_second_paint = False
			self._query.setSelection(
				self._selection_start,
				-1 if self._selection_end is None else
				self._selection_end - self._selection_start
			)
	def _on_text_changed(self, text):
		if self._setting_suggestion:
			return
		super()._on_text_changed(text)
		self._items.setCurrentIndex(self._items.model().index(-1, 0))
		if self._suggestions is not None:
			self._suggestions.request(text)
	def _set_suggestions(self, text, matches):
		if self._query.text() != text:
			return
		self._curr_items = [QuicksearchItem(match) for match in matches]
		model = self._items.model()
		model.clear()
		model.extend(self._curr_items)
		self._adjust_item_list_ize()
		self._items.setCurrentIndex(self._items.model().index(-1, 0))
	def _on_return_pressed(self):
		self._result = self._query.text(), None
		self.accept()
	def _on_item_clicked(self, index):
		if index.isValid():
			self._set_query_from_item(index.row())
	def _on_key_pressed(self, event):
		if event.key() in (Key_Down, Key_Up) and self._curr_items:
			index = self._items.currentIndex()
			step = -1 if event.key() == Key_Up else 1
			if not index.isValid():
				row = len(self._curr_items) - 1 if step < 0 else 0
			else:
				row = (index.row() + step) % len(self._curr_items)
			self._set_query_from_item(row)
			return True
		return super()._on_key_pressed(event)
	def _set_query_from_item(self, row):
		item = self._curr_items[row]
		self._items.setCurrentIndex(self._items.model().index(row, 0))
		self._setting_suggestion = True
		self._query.setText(str(item.value))
		self._query.setCursorPosition(len(self._query.text()))
		self._setting_suggestion = False
