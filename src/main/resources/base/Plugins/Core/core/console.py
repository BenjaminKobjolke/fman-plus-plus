"""Live plugin console widgets and the pane/window presentation helpers."""

from threading import Thread
import traceback

import fman
from core.console_interpreter import ConsoleInterpreter
from core.textviewer_pane import begin_new_view, caret_fix_css, close_view, mount_view
from fman.impl.console_log import get_console_log
from fman.impl.util.qt.thread import run_in_main_thread
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QTextCursor
from PyQt5.QtWidgets import (
	QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget,
)


class _ConsoleOutput(QPlainTextEdit):
	def __init__(self, console):
		super().__init__()
		self._console = console
		self.setReadOnly(True)
		self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
		self.setMaximumBlockCount(get_console_log().MAX_ENTRIES)

	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Escape:
			self._console.close_console()
			return
		super().keyPressEvent(event)


class _ConsoleInput(QLineEdit):
	def __init__(self, console):
		super().__init__()
		self._console = console
		self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))

	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Escape:
			self._console.close_console()
		elif event.key() == Qt.Key_Up:
			self._console.move_history(-1)
		elif event.key() == Qt.Key_Down:
			self._console.move_history(+1)
		else:
			super().keyPressEvent(event)


class ConsoleView(QWidget):
	"""A live log with a small Python prompt, usable in a pane or a window."""

	def __init__(self, pane, namespace, bg, fg, on_close, window_mode=False):
		super().__init__()
		self._pane = pane
		self._on_close = on_close
		self._window_mode = window_mode
		self._history = []
		self._history_index = 0
		self._log = get_console_log()
		self._output = _ConsoleOutput(self)
		self._prompt = QLabel('>>>')
		self._input = _ConsoleInput(self)
		self._input.returnPressed.connect(self._submit)
		self._interpreter = ConsoleInterpreter(
			self._log, namespace
		)
		self._set_prompt_layout()
		self.setFocusProxy(self._input)
		layout = QVBoxLayout(self)
		layout.addWidget(self._output)
		layout.addWidget(self._prompt_row_widget)
		self._output.setStyleSheet(caret_fix_css(bg, fg))
		self._input.setStyleSheet(
			'QLineEdit { color: %s; background-color: %s; }' % (fg, bg)
		)
		self._prompt.setStyleSheet(
			'QLabel { color: %s; background-color: %s; }' % (fg, bg)
		)
		entries = self._log.snapshot_and_subscribe(self._append_entry)
		self._output.setPlainText(''.join(entries))
		if window_mode:
			self.setWindowTitle('fman Console')
			self.resize(800, 500)
			self.setWindowFlag(Qt.Window, True)

	def _set_prompt_layout(self):
		self._prompt_row_widget = QWidget(self)
		self._prompt_row = QHBoxLayout(self._prompt_row_widget)
		self._prompt_row.addWidget(self._prompt)
		self._prompt_row.addWidget(self._input, 1)

	def _append_entry(self, entry):
		bar = self._output.verticalScrollBar()
		was_at_bottom = bar.value() >= bar.maximum()
		cursor = self._output.textCursor()
		cursor.movePosition(QTextCursor.End)
		cursor.insertText(entry)
		if was_at_bottom:
			bar.setValue(bar.maximum())

	def _submit(self):
		line = self._input.text()
		self._input.clear()
		if line:
			self._history.append(line)
			self._history_index = len(self._history)
		self._input.setEnabled(False)
		Thread(target=self._execute, args=(line,), daemon=True).start()

	def _execute(self, line):
		try:
			needs_more = self._interpreter.push(line)
		except BaseException:
			self._log.append(traceback.format_exc())
			needs_more = False
		run_in_main_thread(self._restore_input, needs_more)

	def _restore_input(self, needs_more):
		self._prompt.setText('...' if needs_more else '>>>')
		self._input.setEnabled(True)
		self._input.setFocus()

	def move_history(self, direction):
		if not self._history:
			return
		self._history_index = max(
			0, min(len(self._history), self._history_index + direction)
		)
		line = self._history[self._history_index] if (
			self._history_index < len(self._history)
		) else ''
		self._input.setText(line)

	def close_console(self):
		if self._window_mode:
			self.close()
		else:
			self._on_close()

	def closeEvent(self, event):
		if self._window_mode:
			self._on_close()
		super().closeEvent(event)


@run_in_main_thread
def show_console_in_pane(pane):
	view_data = begin_new_view(pane)
	if view_data is None:
		return
	_widget, bg, fg = view_data
	view = ConsoleView(
		pane, {'fman': fman, 'window': pane.window, 'pane': pane}, bg, fg,
		lambda: close_view(pane._widget),
	)
	mount_view(pane, _widget, view)


_console_window = None


@run_in_main_thread
def show_console_window(pane):
	global _console_window
	if _console_window is None:
		first_pane = pane.window.get_panes()[0]
		bg, fg = first_pane.get_colors()
		_console_window = ConsoleView(
			first_pane,
			{'fman': fman, 'window': first_pane.window, 'pane': first_pane},
			bg, fg, _forget_console_window, window_mode=True,
		)
	_console_window.show()
	_console_window.raise_()
	_console_window.activateWindow()


def _forget_console_window():
	global _console_window
	_console_window = None
