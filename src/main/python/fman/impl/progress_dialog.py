"""Progress dialog for long-running file operations."""

from fbs_runtime.platform import is_windows
from fman import QuicksearchItem
from fman.impl.util.qt.thread import run_in_main_thread
from fman.impl.workers_label import ElidingLabel, WorkersLabel
from PyQt5.QtCore import QTimer, Qt, QEvent, QSize
from PyQt5.QtWidgets import QProgressDialog, QProgressBar, QPushButton, QLabel

class ProgressDialog(QProgressDialog):

	"""
	Instead of using @run_in_main_thread on #set_text(...) and
	#set_progress(...), this class uses #_update_timer to only update the GUI
	every 100ms. This avoids the unnecessary overhead of syncing with the main
	thread for every status update, and thus improves performance.
	"""

	_MAX_C_INT = 2147483647
	_MINIMUM_DURATION_MS = 1000
	_UPDATE_INTERVAL_MS = 100

	@run_in_main_thread
	def __init__(
		self, parent, title, size, progress_bar_palette, options, tool_windows
	):
		# Would like the dialog to be non-resizable on all platforms, but only
		# Windows supports it as a flag. On other platforms, we use
		# setFixedSize(...). See #resizeEvent(...) below.
		args = (Qt.MSWindowsFixedSizeDialogHint,) if is_windows() else ()
		super().__init__(parent, *args)
		self._options = options
		self._tool_windows = tool_windows
		self._tool_windows.register(
			self, options.minimizable and not options.keeps_focus
		)
		if options.keeps_focus:
			self.setWindowModality(Qt.WindowModal)
		self._minimize_button = None
		if options.minimizable and not options.keeps_focus:
			self._minimize_button = QPushButton('–', self)
			self._minimize_button.setObjectName('tool-window-minimize')
			self._minimize_button.setFocusPolicy(Qt.NoFocus)
			self._minimize_button.clicked.connect(self.minimize)
		self._title = title
		self._size = self.maximum()
		self._text = ''
		self._progress = 0
		self._was_canceled = False
		self._workers_label = None
		self._event_filter_installed = False
		self._bar = self.findChild(QProgressBar)
		self._bar.setPalette(progress_bar_palette)
		# Looked up now: the workers label adds buttons of its own later.
		self._cancel_button = self.findChild(QPushButton)
		label = _FixedWidthLabel()
		# setLabel(...) does not re-apply the style's label alignment.
		label.setAlignment(self.findChild(QLabel).alignment())
		self.setLabel(label)
		self.setMinimumDuration(self._MINIMUM_DURATION_MS)
		self.setAutoReset(False)
		self.setWindowTitle(title)
		self.set_task_size(size)
		self.canceled.disconnect(super().cancel)
		self.canceled.connect(self.request_cancel)
		if options.minimizable and not options.keeps_focus:
			self._install_event_filter()
		self._update_timer = QTimer(self)
		self._update_timer.timeout.connect(self._update)
		# Ensure the progress dialog appears in 1 sec starting *now*:
		self.setValue(0)
	def set_text(self, text):
		self._text = text
	@run_in_main_thread
	def set_task_size(self, size):
		self._size = size
		self.setMaximum(min(size, self._MAX_C_INT))
	def set_progress(self, progress):
		self._progress = progress
	def get_progress(self):
		return self._progress
	def reject(self):
		# Called when the user presses the "Close window" button.
		self.request_cancel()
	@run_in_main_thread
	def cancel(self):
		super().cancel()
		self._tool_windows.remove(self)
	def minimize(self):
		if self._options.minimizable and not self._options.keeps_focus:
			self._tool_windows.minimize(
				self, self._title, self._options.icon
			)
	@run_in_main_thread
	def request_cancel(self):
		self.set_text('Canceling...')
		self._cancel_button.setEnabled(False)
		self._was_canceled = True
	@run_in_main_thread
	def show_alert(self, *args, **kwargs):
		return self._show_without_popup(
			self.parent().show_alert, *args, **kwargs
		)
	@run_in_main_thread
	def show_overwrite_dialog(self, *args, **kwargs):
		return self._show_without_popup(
			self.parent().show_overwrite_dialog, *args, **kwargs
		)
	@run_in_main_thread
	def show_prompt(self, *args, **kwargs):
		return self._show_without_popup(
			self.parent().show_prompt, *args, **kwargs
		)
	def _show_without_popup(self, show_dialog, *args, **kwargs):
		# Prevent the progress dialog from popping up while the alert is shown:
		self.setMinimumDuration(self._MAX_C_INT)
		try:
			return show_dialog(*args, **kwargs)
		finally:
			self.setMinimumDuration(self._MINIMUM_DURATION_MS)
	def was_canceled(self):
		return self._was_canceled
	@run_in_main_thread
	def show_workers(self, workers):
		self._workers_label = WorkersLabel(workers, self)
		self.setLabel(self._workers_label)
		self._install_event_filter()
	def _install_event_filter(self):
		if self._event_filter_installed:
			return
		self.installEventFilter(self)
		self._cancel_button.installEventFilter(self)
		self._event_filter_installed = True
	def eventFilter(self, obj, e):
		# Filters the focused Cancel button too: it uses Up / Down itself.
		if e.type() != QEvent.KeyPress:
			return False
		if e.key() == Qt.Key_P and e.modifiers() & Qt.ControlModifier and \
				e.modifiers() & Qt.ShiftModifier:
			self._open_palette()
			return True
		return self._workers_label is not None and \
			self._workers_label.handle_key(e.key())
	def _open_palette(self):
		actions = self._workers_label.palette_actions(
			self.request_cancel
		) if self._workers_label is not None else [
			('Cancel', 'Esc', self.request_cancel)
		]
		if self._options.minimizable and not self._options.keeps_focus:
			actions.insert(len(actions) - 1, ('Minimize', '–', self.minimize))
		def suggest(query):
			# The dialog palette only needs a substring filter for its few actions.
			return [
				QuicksearchItem(action, title, hint=hint)
				for title, hint, action in actions
				if query.lower() in title.lower()
			]
		result = self.parent().show_quicksearch(suggest)
		if result and result[1]:
			result[1]()
	def showEvent(self, e):
		self._tool_windows.shown(self)
		self._update()
		self._update_timer.start(self._UPDATE_INTERVAL_MS)
		super().showEvent(e)
	def closeEvent(self, e):
		self._update_timer.stop()
		super().closeEvent(e)
	def resizeEvent(self, e):
		super().resizeEvent(e)
		# Prevent the dialog from being resizable:
		if not is_windows():
			self.setFixedSize(self.size())
		if self._workers_label is not None:
			self._workers_label.place_file_count(
				self._bar, self._cancel_button
			)
		if self._minimize_button is not None:
			self._minimize_button.move(
				self.width() - self._minimize_button.sizeHint().width() - 8, 4
			)
	def _update(self):
		if self.wasCanceled():
			return
		if self._workers_label is None:
			self.setLabelText(self._text)
		# QLabel#setText(...) is not virtual, so setLabelText(...) would not
		# reach the workers label's own text.
		elif self._workers_label.refresh(self._text):
			self.adjustSize()
		self._set_value(self._progress)
	def _set_value(self, progress):
		if self._size > self._MAX_C_INT:
			# QProgressDialog#setValue(...) can only handle ints. If `progress`
			# is too large, we need to scale it down. If we didn't do this and
			# pass a larger number, it would overflow to a negative value.
			progress = self._MAX_C_INT * progress // self._size
		self.setValue(progress)

class _FixedWidthLabel(ElidingLabel):
	"""
	Asks for no width of its own, so a long file name does not widen the
	dialog with each file: the name is cut in the middle instead.
	"""
	def sizeHint(self):
		return QSize(0, super().sizeHint().height())
