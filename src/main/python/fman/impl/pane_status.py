"""Pane-specific status message modes and their small footer widget."""

from dataclasses import dataclass
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QSizePolicy


@dataclass(frozen=True)
class PaneStatusMode:
	"""The configured destinations for messages sent by a pane."""

	lines_visible: bool
	in_status_bar: bool

	@property
	def copies_to_status_bar(self) -> bool:
		return self.in_status_bar or not self.lines_visible


class PaneStatusLine(QLabel):
	"""A pane footer that appears only while it has an active message."""

	def __init__(self, parent=None):
		super().__init__(parent)
		# Let the label take its height from its font without letting a long
		# message force the pane or splitter to keep a wide minimum size.
		self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
		self.setOpenExternalLinks(True)
		self._enabled = True
		self._idle_text = ''
		self._has_message = False
		self._timer = QTimer(self)
		self._timer.setSingleShot(True)
		self._timer.timeout.connect(self.clear_status_message)
		self.hide()

	def set_status_message(self, text, timeout_secs=None):
		self._has_message = True
		self.setText(text)
		if timeout_secs is None:
			self._timer.stop()
		else:
			self._timer.start(int(timeout_secs * 1000))
		self._update_visibility()

	def clear_status_message(self):
		self._timer.stop()
		self._has_message = False
		self._update_text()
		self._update_visibility()

	def set_idle_text(self, text):
		self._idle_text = text
		self._update_text()
		self._update_visibility()

	def set_status_line_visible(self, visible):
		self._enabled = visible
		self._update_visibility()

	def _update_visibility(self):
		self.setVisible(self._enabled and bool(self.text()))

	def _update_text(self):
		if not self._has_message:
			self.setText(self._idle_text)
