"""In-memory log shared by the plugin console and captured output streams."""

from collections import deque
from datetime import datetime
from threading import Lock, RLock
from PyQt5.QtCore import QObject, pyqtSignal


class ConsoleLog(QObject):
	"""Store recent console entries and notify live views when they arrive."""

	MAX_ENTRIES = 2000
	entry_added = pyqtSignal(str)

	def __init__(self):
		super().__init__()
		self._entries = deque(maxlen=self.MAX_ENTRIES)
		self._lock = RLock()

	@property
	def entries(self):
		with self._lock:
			return tuple(self._entries)

	def snapshot_and_subscribe(self, slot):
		"""Connect a live view and return its initial entries without a gap."""
		with self._lock:
			self.entry_added.connect(slot)
			return tuple(self._entries)

	def append(self, entry):
		with self._lock:
			self._entries.append(entry)
			self.entry_added.emit(entry)

	def append_error(self, headline, traceback):
		entry = '--- {} {} ---\n{}'.format(
			datetime.now().strftime('%H:%M:%S'), headline, traceback.rstrip()
		)
		self.append(entry)
		return entry


class TeeStream:
	"""Forward text to its original stream and capture it in the console log."""

	def __init__(self, original, console_log):
		self._original = original
		self._console_log = console_log
		self.encoding = getattr(original, 'encoding', None)
		self.errors = getattr(original, 'errors', None)

	def write(self, text):
		if self._original is not None:
			self._original.write(text)
		self._console_log.append(text)
		return len(text)

	def flush(self):
		if self._original is not None:
			self._original.flush()

	def isatty(self):
		return self._original is not None and self._original.isatty()

	def fileno(self):
		if self._original is None:
			raise OSError('Stream has no file descriptor')
		return self._original.fileno()


_USE_CURRENT_STREAM = object()


def install_stream_capture(
	console_log,
	stdout=_USE_CURRENT_STREAM,
	stderr=_USE_CURRENT_STREAM
):
	"""Capture writes to stdout and stderr while preserving their original sinks."""
	import sys

	if stdout is _USE_CURRENT_STREAM:
		stdout = sys.stdout
	if stderr is _USE_CURRENT_STREAM:
		stderr = sys.stderr
	if not isinstance(stdout, TeeStream) or stdout._console_log is not console_log:
		sys.stdout = TeeStream(stdout, console_log)
	if not isinstance(stderr, TeeStream) or stderr._console_log is not console_log:
		sys.stderr = TeeStream(stderr, console_log)


def format_log_args(*args):
	"""Format arguments like print(), including its default trailing newline."""
	return ' '.join(str(arg) for arg in args) + '\n'


_console_log = None
_console_log_lock = Lock()


def get_console_log():
	"""Return the process-wide console log, creating it on first use."""
	global _console_log
	with _console_log_lock:
		if _console_log is None:
			_console_log = ConsoleLog()
		return _console_log
