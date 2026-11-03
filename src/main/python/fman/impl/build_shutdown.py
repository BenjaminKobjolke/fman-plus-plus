"""
Lets tools\\close_running_fman.ps1 close fman before a build replaces its files.

The script sends MESSAGE_NAME to our windows. Closing straight away could cut
off a file operation, so fman shows a countdown instead, which the user can
cancel with Esc. When it runs out, fman quits the normal way and so saves its
session. Windows only: the request is a native window message.
"""

from ctypes import windll
from ctypes.wintypes import MSG
from fman import APP_NAME
from fman.impl.countdown import Countdown
from PyQt5.QtCore import QAbstractNativeEventFilter, QTimer

# Must match $MessageName in tools\close_running_fman.ps1.
MESSAGE_NAME = 'fman.CloseForBuild'
_TEXT = (
	'Closing ' + APP_NAME + ' for a build in %d s.\n'
	'Press Esc to keep it running.'
)

class BuildShutdownFilter(QAbstractNativeEventFilter):
	def __init__(self, main_window, quit_):
		super().__init__()
		self._main_window = main_window
		self._quit = quit_
		self._message_id = windll.user32.RegisterWindowMessageW(MESSAGE_NAME)
		self._counting_down = False
	def is_counting_down(self):
		return self._counting_down
	def nativeEventFilter(self, event_type, message):
		if bytes(event_type) != b'windows_generic_MSG':
			return False, 0
		msg = MSG.from_address(int(message))
		if msg.message != self._message_id:
			return False, 0
		if not self._counting_down:
			self._counting_down = True
			seconds = msg.wParam
			# Not right here: the script waits in SendMessageTimeout for the
			# answer below, and the countdown runs a nested event loop.
			QTimer.singleShot(0, lambda: self._count_down(seconds))
		# 1 tells the script that the countdown runs. An older fman answers 0,
		# and the script then falls back to closing the main window.
		return True, 1
	def _count_down(self, seconds):
		try:
			countdown = Countdown(self._main_window, _TEXT, seconds)
			# The build runs in another window, so fman is rarely in front.
			countdown.shown.connect(countdown.activateWindow)
			if self._main_window.exec_dialog(countdown) == Countdown.Ok:
				self._quit()
		finally:
			self._counting_down = False
