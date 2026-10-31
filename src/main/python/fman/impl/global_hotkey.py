"""Register and dispatch Windows-wide keyboard shortcuts."""

from ctypes import windll
from ctypes.wintypes import MSG
from PyQt5.QtCore import QAbstractNativeEventFilter, Qt, QTimer

from fman.impl.util.qt.key_events import parse_chord

SETTING = 'global_hotkey'
HOTKEY_ID = 1
WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_QT_MODIFIERS = {
	int(Qt.AltModifier): MOD_ALT,
	int(Qt.ControlModifier): MOD_CONTROL,
	int(Qt.ShiftModifier): MOD_SHIFT,
	int(Qt.MetaModifier): MOD_WIN,
}
_NAVIGATION_KEYS = {
	Qt.Key_Backspace: 0x08,
	Qt.Key_Tab: 0x09,
	Qt.Key_Return: 0x0D,
	Qt.Key_Enter: 0x0D,
	Qt.Key_Escape: 0x1B,
	Qt.Key_Space: 0x20,
	Qt.Key_PageUp: 0x21,
	Qt.Key_PageDown: 0x22,
	Qt.Key_End: 0x23,
	Qt.Key_Home: 0x24,
	Qt.Key_Left: 0x25,
	Qt.Key_Up: 0x26,
	Qt.Key_Right: 0x27,
	Qt.Key_Down: 0x28,
	Qt.Key_Insert: 0x2D,
	Qt.Key_Delete: 0x2E,
}


def parse_hotkey(chord):
	"""Return (Win32 modifiers, virtual key) or None for an empty setting."""
	if not chord:
		return None
	# Qt names the Windows key Meta; the setting uses the familiar Windows name.
	qt_chord = '+'.join(
		'Meta' if part.strip().casefold() == 'win' else part.strip()
		for part in chord.split('+')
	)
	key, qt_modifiers = parse_chord(qt_chord)
	modifiers = 0
	remaining = int(qt_modifiers)
	for qt_modifier, win_modifier in _QT_MODIFIERS.items():
		if remaining & qt_modifier:
			modifiers |= win_modifier
			remaining &= ~qt_modifier
	if remaining:
		raise ValueError('Unsupported modifier in global hotkey: %r' % chord)

	if Qt.Key_A <= key <= Qt.Key_Z:
		virtual_key = ord('A') + key - Qt.Key_A
	elif Qt.Key_0 <= key <= Qt.Key_9:
		virtual_key = ord('0') + key - Qt.Key_0
	elif Qt.Key_F1 <= key <= Qt.Key_F24:
		virtual_key = 0x70 + key - Qt.Key_F1
	else:
		virtual_key = _NAVIGATION_KEYS.get(key)
	if virtual_key is None:
		raise ValueError('Unsupported key in global hotkey: %r' % chord)
	return modifiers, virtual_key


class GlobalHotkey(QAbstractNativeEventFilter):
	def __init__(self, callback, show_status):
		super().__init__()
		self._callback = callback
		self._show_status = show_status
		self._registered = False
	def register(self, chord):
		self.unregister()
		if not chord:
			return None
		try:
			modifiers, virtual_key = parse_hotkey(chord)
		except ValueError:
			self._show_status('Invalid global hotkey: %s' % chord)
			return False
		# hWnd=NULL makes WM_HOTKEY a thread message, so it survives window
		# recreation when window_chrome changes the native HWND.
		if not windll.user32.RegisterHotKey(
			None, HOTKEY_ID, modifiers | MOD_NOREPEAT, virtual_key
		):
			self._show_status('Global hotkey is already in use: %s' % chord)
			return False
		self._registered = True
		return True
	def unregister(self):
		if self._registered:
			windll.user32.UnregisterHotKey(None, HOTKEY_ID)
			self._registered = False
	def nativeEventFilter(self, event_type, message):
		if bytes(event_type) not in (
			b'windows_generic_MSG', b'windows_dispatcher_MSG'
		):
			return False, 0
		msg = MSG.from_address(int(message))
		if msg.message != WM_HOTKEY or msg.wParam != HOTKEY_ID:
			return False, 0
		QTimer.singleShot(0, self._callback)
		return True, 0
