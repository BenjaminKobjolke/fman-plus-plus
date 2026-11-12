"""Load prompt path suggestions without blocking the GUI thread."""

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from threading import Event, Lock, Thread
import logging


_LOG = logging.getLogger(__name__)


class PromptSuggestions(QObject):
	_results_ready = pyqtSignal(str, object)

	def __init__(self, get_completions, on_results, parent=None):
		super().__init__(parent)
		self._get_completions = get_completions
		self._on_results = on_results
		self._pending_event = Event()
		self._lock = Lock()
		self._pending_text = None
		self._latest_text = None
		self._closed = False
		self._results_ready.connect(self._apply_results)
		self._timer = QTimer(self)
		self._timer.setSingleShot(True)
		self._timer.setInterval(150)
		self._timer.timeout.connect(self._queue_latest)
		self._worker = Thread(target=self._work, daemon=True)
		self._worker.start()

	def request(self, text):
		if self._closed:
			return
		self._latest_text = text
		self._timer.start()

	def close(self):
		with self._lock:
			self._closed = True
			self._pending_text = None
		self._pending_event.set()
		self._timer.stop()

	def _queue_latest(self):
		with self._lock:
			if self._closed:
				return
			self._pending_text = self._latest_text
		self._pending_event.set()

	def _work(self):
		while True:
			self._pending_event.wait()
			with self._lock:
				if self._closed:
					return
				text = self._pending_text
				self._pending_text = None
				self._pending_event.clear()
			if text is None:
				continue
			try:
				matches = list(self._get_completions(text))
			except Exception:
				_LOG.exception('Could not load prompt path suggestions for %r.', text)
				matches = []
			try:
				with self._lock:
					if self._closed:
						return
					self._results_ready.emit(text, matches)
			except RuntimeError:
				# The prompt may have closed while the filesystem was being listed.
				return

	def _apply_results(self, text, matches):
		if not self._closed and text == self._latest_text:
			self._on_results(text, matches)
