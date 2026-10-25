from fbs_runtime.application_context import is_frozen
from fbs_runtime.excepthook import ExceptionHandler
from fman.impl.theme import ThemeError
from fman.impl.util import is_below_dir
from os.path import dirname, basename
from traceback import StackSummary, extract_tb, TracebackException, \
	print_exception

import fman
import sys
from PyQt5.QtWidgets import QMessageBox
from fman.impl.console_log import get_console_log

class PluginErrorHandler(ExceptionHandler):
	def __init__(self, app, console_log=None, open_console=None):
		self._app = app
		self._console_log = console_log or get_console_log()
		self._open_console = open_console or (lambda: None)
		self._main_window = None
		self._pending_errors = []
		self._plugin_dirs = []
	def add_dir(self, plugin_dir):
		self._plugin_dirs.append(plugin_dir)
	def remove_dir(self, plugin_dir):
		self._plugin_dirs.remove(plugin_dir)
	def handle(self, exc_type, exc_value, enriched_tb):
		causing_plugin = self._get_plugin_causing_error(enriched_tb)
		if causing_plugin and basename(causing_plugin) != 'Core':
			self.report(
				'Plugin %r raised an error.' % basename(causing_plugin),
				exc_value
			)
			return True
	def _get_plugin_causing_error(self, traceback):
		for frame in extract_tb(traceback):
			for plugin_dir in self._plugin_dirs:
				if is_below_dir(frame.filename, plugin_dir):
					return plugin_dir
	def report(self, message, exc=None):
		if exc is None:
			exc = sys.exc_info()[1]
		traceback = ''
		if exc:
			if not is_frozen():
				# The steps further below only show a pruned stack trace. During
				# development, it's useful to retain the full trace in the terminal.
				stderr = getattr(sys.stderr, '_original', sys.__stderr__)
				if stderr is not None:
					print_exception(
						type(exc), exc, exc.__traceback__, file=stderr
					)
			traceback = self._get_plugin_traceback(exc)
		self._console_log.append_error(message, traceback)
		details = message + ('\n\n' + traceback if traceback else '')
		if self._main_window:
			self._show_error_alert(message, details)
		else:
			self._pending_errors.append((message, details))
	def _show_error_alert(self, headline, details):
		buttons = QMessageBox.Cancel | QMessageBox.Open | QMessageBox.Save
		result = self._main_window.show_alert(
			headline, buttons=buttons, default_button=QMessageBox.Cancel,
			button_texts={
				QMessageBox.Cancel: 'Dismiss',
				QMessageBox.Open: 'Open in console',
				QMessageBox.Save: 'Copy error',
			}
		)
		if result == QMessageBox.Open:
			self._open_console()
		elif result == QMessageBox.Save:
			fman.clipboard.set_text(details)
			self._main_window.show_status_message(
				'Error copied to clipboard.', timeout_secs=3
			)
	def handle_system_exit(self, code=0):
		self._app.exit(code)
	def on_main_window_shown(self, main_window):
		self._main_window = main_window
		if self._pending_errors:
			headline, details = self._pending_errors[0]
			self._show_error_alert(headline, details)
	def _get_plugin_traceback(self, exc):
		if isinstance(exc, ThemeError):
			return exc.description
		return format_traceback(exc, exclude_dirs=[dirname(fman.__file__)])

def format_traceback(exc, exclude_dirs):
	def tb_filter(tb):
		tb_file = extract_tb(tb)[0][0]
		for dir_ in exclude_dirs:
			if is_below_dir(tb_file, dir_):
				return False
		return True
	traceback_ = \
		TracebackExceptionWithTbFilter.from_exception(exc, tb_filter=tb_filter)
	return ''.join(traceback_.format())

class TracebackExceptionWithTbFilter(TracebackException):
	"""
	Copied and adapted from Python's `TracebackException`. Adds one
	additional constructor arg: `tb_filter`, a boolean predicate that determines
	which traceback entries should be included.
	"""
	@classmethod
	def from_exception(cls, exc, *args, **kwargs):
		return cls(type(exc), exc, exc.__traceback__, *args, **kwargs)
	def __init__(
		self, exc_type, exc_value, exc_traceback, *, limit=None,
		lookup_lines=True, capture_locals=False, _seen=None,
		tb_filter=None
	):
		if _seen is None:
			_seen = set()
		_seen.add(id(exc_value))
		# Let super handle all standard attributes (exc_type, _str,
		# exceptions, etc.) — some became read-only properties in Python 3.14.
		super().__init__(
			exc_type, exc_value, exc_traceback,
			limit=limit, lookup_lines=False,
			capture_locals=capture_locals
		)
		# Override cause/context with tb_filter-aware versions
		if (exc_value and exc_value.__cause__ is not None
			and id(exc_value.__cause__) not in _seen):
			self.__cause__ = TracebackExceptionWithTbFilter(
				type(exc_value.__cause__),
				exc_value.__cause__,
				exc_value.__cause__.__traceback__,
				limit=limit,
				lookup_lines=False,
				capture_locals=capture_locals,
				_seen=_seen,
				tb_filter=tb_filter
			)
		if (exc_value and exc_value.__context__ is not None
			and id(exc_value.__context__) not in _seen):
			self.__context__ = TracebackExceptionWithTbFilter(
				type(exc_value.__context__),
				exc_value.__context__,
				exc_value.__context__.__traceback__,
				limit=limit,
				lookup_lines=False,
				capture_locals=capture_locals,
				_seen=_seen,
				tb_filter=tb_filter
			)
		# Override stack with filtered version
		self.stack = StackSummary.extract(
			walk_tb_with_filtering(exc_traceback, tb_filter), limit=limit,
			lookup_lines=lookup_lines, capture_locals=capture_locals
		)
		if exc_value:
			context = self.__context__
			# Hide context when all its frames are hidden:
			self.__suppress_context__ = exc_value.__suppress_context__ or \
										(context and not context.stack.format())
		if lookup_lines:
			self._load_lines()

def walk_tb_with_filtering(tb, tb_filter=None):
	while tb is not None:
		if tb_filter is None or tb_filter(tb):
			yield tb.tb_frame, tb.tb_lineno
		tb = tb.tb_next
