"""Asynchronous Tab cycling for line edits in destination prompts."""
from PyQt5.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication
from threading import Thread
import logging


_LOG = logging.getLogger(__name__)


class PromptTabCompletion(QObject):
	"""Run completion callbacks off-thread and apply their results on the GUI."""
	_results_ready = pyqtSignal(str, object)

	def __init__(self, line_edit, get_completions):
		super().__init__(line_edit)
		self._line_edit = line_edit
		self._get_completions = get_completions
		self._in_flight = set()
		self._matches = []
		self._match_index = None
		self._last_applied = None
		self._applying = False
		self._results_ready.connect(self._apply_results)
		self._line_edit.installEventFilter(self)
		self._line_edit.textChanged.connect(self._clear_cycle)

	def eventFilter(self, watched, event):
		if watched is self._line_edit and event.type() == QEvent.KeyPress \
				and event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
			self._complete(event.key() == Qt.Key_Backtab or
				bool(event.modifiers() & Qt.ShiftModifier))
			return True
		return False

	def _complete(self, backwards):
		text = self._line_edit.text()
		if text == self._last_applied and self._matches:
			direction = -1 if backwards else 1
			self._match_index = (self._match_index + direction) % len(self._matches)
			self._apply(self._matches[self._match_index])
			return
		if text in self._in_flight:
			return
		self._in_flight.add(text)
		Thread(target=self._load, args=(text,), daemon=True).start()

	def _load(self, text):
		try:
			matches = self._get_completions(text)
		except Exception:
			_LOG.exception('Could not load prompt path completions for %r.', text)
			matches = []
		try:
			self._results_ready.emit(text, list(matches))
		except RuntimeError:
			# The dialog may have closed while the filesystem was being listed.
			pass

	def _apply_results(self, text, matches):
		self._in_flight.discard(text)
		if not self._line_edit.window().isVisible() or \
				self._line_edit.text() != text:
			return
		self._matches = matches
		if not matches:
			QApplication.beep()
			return
		self._match_index = 0
		self._apply(matches[0])

	def _apply(self, text):
		self._applying = True
		self._line_edit.setText(text)
		self._line_edit.deselect()
		self._line_edit.setCursorPosition(len(text))
		self._last_applied = text
		self._applying = False

	def _clear_cycle(self, _text):
		if self._applying:
			return
		self._matches = []
		self._match_index = None
		self._last_applied = None
