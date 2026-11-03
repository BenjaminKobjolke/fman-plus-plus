"""A cancelable message box with a progress bar and a timed result."""

from fman.impl.widgets import MessageBox
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialogButtonBox, QProgressBar

class Countdown(MessageBox):
	def __init__(self, parent, text_template, seconds):
		super().__init__(parent)
		self._text_template = text_template
		self._seconds_left = seconds
		self.setStandardButtons(self.Cancel)
		self.setDefaultButton(self.Cancel)
		self.setText(text_template % seconds)
		self._progress = QProgressBar(self)
		self._progress.setRange(0, seconds)
		self._progress.setValue(seconds)
		self._progress.setTextVisible(False)
		self._add_progress_before_buttons()
		self._timer = QTimer(self)
		self._timer.timeout.connect(self._tick)
		self.finished.connect(self._stop_timer)
		self._timer.start(1000)
	def _stop_timer(self, _result):
		self._timer.stop()
	def _add_progress_before_buttons(self):
		layout = self.layout()
		button_box = self.findChild(QDialogButtonBox)
		index = layout.indexOf(button_box)
		row, column, row_span, column_span = layout.getItemPosition(index)
		layout.removeWidget(button_box)
		layout.addWidget(self._progress, row, 0, 1, layout.columnCount())
		layout.addWidget(
			button_box, row + 1, column, row_span, column_span
		)
	def _tick(self):
		self._seconds_left -= 1
		self._progress.setValue(self._seconds_left)
		if self._seconds_left > 0:
			self.setText(self._text_template % self._seconds_left)
		else:
			self._timer.stop()
			self.done(self.Ok)
