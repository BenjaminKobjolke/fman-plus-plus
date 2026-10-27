"""Tutorial overlay widgets."""

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import (
	QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget,
	QPushButton, QApplication,
)

ARROW_KEY_OFFSETS = {
	Qt.Key_Left: -1, Qt.Key_Up: -1, Qt.Key_Right: 1, Qt.Key_Down: 1
}

class Overlay(QFrame):

	"""
	The tutorial's speech bubble. `takes_focus` decides who owns the keyboard
	while it is up: with it off (the default) the directory pane keeps focus,
	so the user can carry out the step's instructions - navigate, press Tab,
	press F5 - and the overlay's buttons are mouse-only. With it on, the
	last button (the affirmative one, by convention) starts focused, the arrow
	keys move between the buttons and Enter activates the focused one - for
	steps whose only remaining action is "go on".
	"""

	def __init__(self, parent, html, buttons=None, takes_focus=False):
		super().__init__(parent)
		self._takes_focus = takes_focus
		self._default_button = None
		self._focusable_buttons = []
		self._focus_before_show = None

		self.setFrameShape(QFrame.Box)
		self.setFrameShadow(QFrame.Raised)
		self.setFocusPolicy(Qt.NoFocus)

		layout = QVBoxLayout()
		layout.setContentsMargins(20, 20, 20, 20)

		self.label = QLabel(self)
		self.label.setWordWrap(True)
		self.label.setText(html)

		# The following two lines prevent the label from being "cut off" at the
		# bottom under some circumstances:
		layout.setSizeConstraint(layout.SetMinAndMaxSize)
		self.label.setSizePolicy(
			QSizePolicy.MinimumExpanding, QSizePolicy.Minimum
		)

		layout.addWidget(self.label)

		if buttons:
			button_container = QWidget(self)
			button_layout = QHBoxLayout()
			for button_label, action in buttons:
				button = QPushButton(button_label, button_container)
				button.clicked.connect(lambda *_, action=action: action())
				if takes_focus:
					button.setFocusPolicy(Qt.StrongFocus)
					# Enter activates whichever button has focus. Qt draws that
					# one as the default button, so the user can see where
					# Enter would go.
					button.setAutoDefault(True)
					# For the arrow keys - see #eventFilter(...):
					button.installEventFilter(self)
					self._focusable_buttons.append(button)
				else:
					# Prevent button from stealing focus from the directory
					# pane:
					button.setFocusPolicy(Qt.NoFocus)
				button_layout.addWidget(button)
				self._default_button = button
			if takes_focus:
				# The affirmative button is the one Enter hits to begin with.
				self._default_button.setDefault(True)
			button_container.setLayout(button_layout)
			layout.addWidget(button_container)

		self.setLayout(layout)
	def eventFilter(self, watched, event):
		# Qt only moves focus with Tab/Backtab, and MainWindow claims Tab for
		# switching panes (see its #focusNextPrevChild(...)). So we move focus
		# between our buttons ourselves, on the arrow keys the rest of fman
		# uses for navigation. The buttons' Alt+letter mnemonics ("&Yes") work
		# regardless of focus and stay as a shortcut.
		if event.type() == QEvent.KeyPress:
			offset = ARROW_KEY_OFFSETS.get(event.key())
			if offset is not None and self._focus_button(watched, offset):
				return True
		return super().eventFilter(watched, event)
	def _focus_button(self, from_button, offset):
		buttons = self._focusable_buttons
		if len(buttons) < 2 or from_button not in buttons:
			return False
		index = (buttons.index(from_button) + offset) % len(buttons)
		buttons[index].setFocus(Qt.OtherFocusReason)
		return True
	def showEvent(self, event):
		super().showEvent(event)
		if self._takes_focus and self._default_button is not None:
			self._focus_before_show = QApplication.focusWidget()
			self._default_button.setFocus(Qt.OtherFocusReason)
	def close(self):
		self._restore_focus()
		self.setParent(None)
	def _restore_focus(self):
		if self._focus_before_show is None:
			return
		try:
			# Hand the keyboard back to the directory pane, so the next tour
			# step's instructions ("press Tab", "type its name") reach it:
			self._focus_before_show.setFocus(Qt.OtherFocusReason)
		except RuntimeError:
			# The widget that had focus is gone - it was a dialog that has
			# since been closed. Qt then picks the next focus target itself.
			pass
		self._focus_before_show = None
