"""Destination prompt displayed with the Quicksearch popup."""

from fman import QuicksearchItem
from fman.impl.prompt_completion import PromptTabCompletion
from fman.impl.prompt_suggestions import PromptSuggestions
from fman.impl.quicksearch import Quicksearch
from fman.impl.util.qt import Key_Down, Key_Up
from PyQt5.QtWidgets import QDialog, QLineEdit


class Prompt(Quicksearch):
	def __init__(
		self, parent, app, css, message='', default='', selection_start=0,
		selection_end=None, get_completions=None, password=False,
		width_store=None
	):
		super().__init__(
			parent, app, css, lambda _query: [], query=default,
			width_store=width_store, title=message
		)
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
	def setTextValue(self, text):
		self._query.setText(text)
	def textValue(self):
		return self._query.text()
	def labelText(self):
		return self._header.text()
	def setVisible(self, visible):
		if visible:
			self._query.end(False)
			self._request_immediate_repaint = True
		QDialog.setVisible(self, visible)
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
