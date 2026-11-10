"""Log every thread's stack when the GUI thread stops handling events."""

from datetime import datetime
from os import makedirs
from os.path import dirname, getsize
from PyQt5.QtCore import QObject, QTimer
from threading import Event, Thread, enumerate as enumerate_threads

import sys
import time
import traceback

STALL_SECONDS = 5
CHECK_INTERVAL_SECONDS = 1
# shortcut: truncate instead of rotating, upgrade if older entries matter.
MAX_LOG_BYTES = 1024 * 1024


class HangLog(QObject):
	"""A main-thread heartbeat plus a watcher thread that logs stalls."""

	def __init__(self, log_path, clock=time.monotonic):
		super().__init__()
		self._log_path = log_path
		self._clock = clock
		self._last_beat = clock()
		self._stall_logged = False
		self._stall_start = None
		self._timer = QTimer(self)
		self._timer.setInterval(CHECK_INTERVAL_SECONDS * 1000)
		self._timer.timeout.connect(self.beat)
	def start(self):
		self.beat()
		self._timer.start()
		Thread(target=self._monitor, daemon=True, name='HangLog').start()
	def beat(self):
		self._last_beat = self._clock()
	def check_stall(self):
		stalled_for = self._clock() - self._last_beat
		if stalled_for > STALL_SECONDS:
			if not self._stall_logged:
				self._stall_logged = True
				self._stall_start = self._last_beat
				self._write(
					'GUI thread stalled for %.1f s.\n\n%s' %
					(stalled_for, _format_all_stacks())
				)
		elif self._stall_logged:
			self._stall_logged = False
			self._write(
				'GUI thread responsive again after %.1f s.' %
				(self._last_beat - self._stall_start)
			)
	def _monitor(self):
		wait = Event().wait
		while True:
			wait(CHECK_INTERVAL_SECONDS)
			self.check_stall()
	def _write(self, text):
		# A diagnostic log must never break fman, so I/O errors are ignored.
		try:
			makedirs(dirname(self._log_path), exist_ok=True)
			mode = 'a'
			try:
				if getsize(self._log_path) > MAX_LOG_BYTES:
					mode = 'w'
			except OSError:
				pass
			with open(self._log_path, mode, encoding='utf-8') as log_file:
				log_file.write('[%s]\n%s\n\n' % (
					datetime.now().isoformat(timespec='seconds'), text
				))
		except OSError:
			pass


def _format_all_stacks():
	names = {thread.ident: thread.name for thread in enumerate_threads()}
	parts = []
	for ident, frame in sys._current_frames().items():
		parts.append('Thread %s (%s):\n%s' % (
			ident, names.get(ident, '?'),
			''.join(traceback.format_stack(frame))
		))
	return '\n'.join(parts)
