"""Demo playback for the automated-application-screenshots recording tool.

fman opts into that tool's contract (see the tool repo's
docs/AUTOMATION_INTERFACE.md): in demo mode it plays a scripted sequence of UI
actions and reports demo_started/screenshot/demo_ended events over a socket so
the tool can record a GIF/MP4 plus PNG stills.

The reusable step model, socket client and CLI parser come from the stdlib-only
core of the ``automated_screenshot_connector`` library (installed via
the ``demos`` group in pyproject.toml). The library also ships a Qt player, but it
hard-imports PySide6 while fman is a PyQt5 app, so ``DemoPlayer`` below is a
PyQt5 port of the library's ``KeyEventDemoPlayer``: it posts real key events to
the focused widget, which also reaches fman's modal Quicksearch dialog (command
palette / inline filter) since QTimers keep firing inside nested modal loops.

The scripts it plays live in ``demo_scripts.py``.
"""

from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtWidgets import QApplication
from fman.impl.util.qt.key_events import parse_chord, post_chord, post_text

from automated_screenshot_connector.steps import (
	CustomStep, InsertChar, PressReturn, SendKey, SendScreenshot, flatten,
)

# Let the window finish its first paint before the demo starts typing.
START_DELAY_MS = 500
# Hold the final state briefly so the recording doesn't end abruptly.
END_HOLD_MS = 1000

class DemoPlayer(QObject):
	"""Plays one DemoScript by posting key events, then quits the app.

	Everything runs off single-shot QTimers so the event loop never blocks and
	the UI paints exactly as it would for human input.
	"""

	def __init__(self, window, client, script, hwnd):
		super().__init__(window)
		self._window = window
		self._client = client
		self._script = script
		self._hwnd = hwnd
		self._actions = flatten(script.steps)
		self._index = 0
		self._check_chords()

	def _check_chords(self):
		"""Reject an unparsable chord now, not minutes into a recording."""
		for _, action in self._actions:
			if isinstance(action, SendKey):
				self._parse_chord(action.chord)

	def start(self):
		QTimer.singleShot(START_DELAY_MS, self._begin)

	def _begin(self):
		self._client.send_started(self._script.id, self._hwnd)
		self._advance()

	def _advance(self):
		if self._index >= len(self._actions):
			self._finish()
			return
		delay, action = self._actions[self._index]
		self._index += 1
		QTimer.singleShot(delay, lambda: self._execute(action))

	def _execute(self, action):
		if isinstance(action, InsertChar):
			self._send_char(action.char)
		elif isinstance(action, PressReturn):
			self._send_chord('Return')
		elif isinstance(action, SendKey):
			self._send_chord(action.chord)
		elif isinstance(action, SendScreenshot):
			self._client.send_screenshot(action.name)
		elif isinstance(action, CustomStep):
			# fman defines no custom steps; a Wait's delay already elapsed.
			pass
		self._advance()

	def _target(self):
		return QApplication.focusWidget() or self._window

	def _send_char(self, ch):
		post_text(self._target(), ch)

	def _parse_chord(self, chord):
		return parse_chord(chord)

	def _send_chord(self, chord):
		post_chord(self._target(), chord)

	def _finish(self):
		self._client.send_ended(self._script.id)
		self._client.close()
		instance = QApplication.instance()
		if instance is not None:
			QTimer.singleShot(END_HOLD_MS, instance.quit)
