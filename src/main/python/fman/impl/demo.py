"""Demo playback for the automated-application-screenshots recording tool.

fman opts into that tool's contract (see the tool repo's
docs/AUTOMATION_INTERFACE.md): in demo mode it plays a scripted sequence of UI
actions and reports demo_started/screenshot/demo_ended events over a socket so
the tool can record a GIF/MP4 plus PNG stills. fman renders each still itself
with Qt and uploads it inline; video frames and ``ScreenStill`` steps are
captured by the tool from the screen.

The reusable step model, socket client and CLI parser come from the stdlib-only
core of the ``automated_screenshot_connector`` library (installed via
the ``demos`` group in pyproject.toml). The library also ships a Qt player, but it
hard-imports PySide6 while fman is a PyQt5 app, so ``DemoPlayer`` below is a
PyQt5 port of the library's ``KeyEventDemoPlayer``: it posts real key events to
the focused widget, which also reaches fman's modal Quicksearch dialog (command
palette / inline filter) since QTimers keep firing inside nested modal loops.

The scripts it plays live in ``demo_scripts.py``.
"""

from dataclasses import dataclass
import os
import subprocess
import sys
import time

from PyQt5.QtCore import QObject, QTimer
from PyQt5.QtGui import QContextMenuEvent
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QMenu
from fman.impl.util.qt.key_events import (
	parse_chord, post_chord, post_text,
)
from fman.impl.demo_window import foreground_process_window

from automated_screenshot_connector.steps import (
	CustomStep, InsertChar, PressReturn, SendKey, SendScreenshot, flatten,
)

# Let the window finish its first paint before the demo starts typing.
START_DELAY_MS = 500
# Hold the final state briefly so the recording doesn't end abruptly.
END_HOLD_MS = 1000


@dataclass(frozen=True)
class OpenContextMenu:
	"""Open the file context menu for the cursor's row, like the Menu key."""


@dataclass(frozen=True)
class ScreenStill:
	"""Ask the recording tool to capture a still directly from the screen.

	Separate windows such as the progress window are included in the capture.
	"""
	name: str


@dataclass(frozen=True)
class LaunchFman:
	"""Launch another fman process with arguments relative to the active pane."""

	args: tuple[str, ...]


@dataclass(frozen=True)
class ExpectChildWindow:
	"""Bring the most recently launched fman window to the foreground."""

	timeout_s: float = 20.0


@dataclass(frozen=True)
class ExpectForwarded:
	"""Wait for a normal launch to forward to this demo's active pane."""

	folder: str
	timeout_s: float = 20.0


@dataclass(frozen=True)
class WaitForOverwriteQuestion:
	"""Capture and answer the overwrite question, failing if it never opens."""

	timeout_s: float = 30.0


class DemoPlayer(QObject):
	"""Plays one DemoScript by posting key events, then quits the app.

	Everything runs off single-shot QTimers so the event loop never blocks and
	the UI paints exactly as it would for human input.
	"""

	def __init__(self, window, client, script, hwnd, screenshots, plugin_support):
		super().__init__(window)
		self._window = window
		self._client = client
		self._script = script
		self._hwnd = hwnd
		self._screenshots = screenshots
		self._plugin_support = plugin_support
		self._children = []
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
			self._client.send_screenshot(
				action.name, png=self._screenshots.screenshot_png())
		elif isinstance(action, CustomStep):
			if isinstance(action.step, OpenContextMenu):
				self._open_context_menu()
			elif isinstance(action.step, ScreenStill):
				self._client.send_screenshot(action.step.name)
			elif isinstance(action.step, WaitForOverwriteQuestion):
				self._wait_for_overwrite_question(action.step)
				return
			elif isinstance(action.step, LaunchFman):
				self._launch_fman(action.step)
			elif isinstance(action.step, ExpectChildWindow):
				self._expect_child_window(action.step)
				return
			elif isinstance(action.step, ExpectForwarded):
				self._expect_forwarded(action.step)
				return
			# Other custom steps remain ignored; a Wait's delay already elapsed.
		self._advance()

	def _wait_for_overwrite_question(self, step):
		from fman.impl.overwrite_dialog import OverwriteDialog
		from fman.impl.progress_dialog import ProgressDialog

		deadline = time.monotonic() + step.timeout_s

		def check():
			dialogs = self._window.findChildren(OverwriteDialog)
			dialog = next(
				(dialog for dialog in dialogs if dialog.isVisible()), None
			)
			progress_is_visible = any(
				window.isVisible()
				for window in self._window.findChildren(ProgressDialog)
			)
			if dialog is not None and not progress_is_visible:
				self._client.send_screenshot('ftp-overwrite-question')

				def answer():
					post_chord(dialog, 'Return')
					self._advance()

				# ScreenStill is captured on the tool's next screen frame.
				QTimer.singleShot(1000, answer)
			elif time.monotonic() >= deadline:
				self._fail()
			else:
				QTimer.singleShot(100, check)

		check()

	def _launch_fman(self, step):
		base_path = self._plugin_support.get_panes()[0].get_path()
		args = [
			arg if arg.startswith('--') else os.path.join(base_path, arg)
			for arg in step.args
		]
		self._children.append(subprocess.Popen([
			sys.executable, os.path.abspath(sys.argv[0]), *args,
		]))

	def _expect_child_window(self, step):
		deadline = time.monotonic() + step.timeout_s

		def check():
			child = self._children[-1] if self._children else None
			if (
				child is not None
				and child.poll() is None
				and foreground_process_window(child.pid)
			):
				self._advance()
			elif time.monotonic() >= deadline:
				self._fail()
			else:
				QTimer.singleShot(100, check)

		check()

	def _expect_forwarded(self, step):
		deadline = time.monotonic() + step.timeout_s

		def check():
			recent_child = self._children[-1] if self._children else None
			active_pane = self._plugin_support.get_active_pane()
			if (
				recent_child is not None
				and recent_child.poll() == 0
				and active_pane is not None
				and active_pane.get_path().endswith(step.folder)
				and all(child.poll() is None for child in self._children[:-1])
			):
				self._advance()
			elif time.monotonic() >= deadline:
				self._fail()
			else:
				QTimer.singleShot(100, check)

		check()

	def _terminate_children(self):
		for child in self._children:
			if child.poll() is None:
				child.terminate()

	def _fail(self):
		"""Close a failed recording instead of raising from a timer callback."""
		self._terminate_children()
		self._client.close()
		instance = QApplication.instance()
		if instance is not None:
			instance.quit()

	def _target(self):
		popup = QApplication.activePopupWidget()
		if isinstance(popup, QMenu):
			# The file view keeps focus while a menu is open, so Escape must target
			# the menu.
			return popup
		return QApplication.focusWidget() or self._window

	def _open_context_menu(self):
		view = QApplication.focusWidget()
		if not isinstance(view, QAbstractItemView):
			raise ValueError('OpenContextMenu needs a focused file view')
		point = view.visualRect(view.currentIndex()).center()
		# Right-button selection swallows Mouse; a posted Menu key bypasses
		# Qt's context-menu path.
		QApplication.postEvent(
			view.viewport(),
			QContextMenuEvent(
				QContextMenuEvent.Keyboard,
				point,
				view.viewport().mapToGlobal(point),
			),
		)

	def _send_char(self, ch):
		post_text(self._target(), ch)

	def _parse_chord(self, chord):
		return parse_chord(chord)

	def _send_chord(self, chord):
		post_chord(self._target(), chord)

	def _finish(self):
		self._terminate_children()
		self._client.send_ended(self._script.id)
		self._client.close()
		instance = QApplication.instance()
		if instance is not None:
			QTimer.singleShot(END_HOLD_MS, instance.quit)
