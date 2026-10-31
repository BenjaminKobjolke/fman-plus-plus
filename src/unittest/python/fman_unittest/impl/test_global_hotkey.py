import sys
import unittest

if sys.platform != 'win32':
	raise unittest.SkipTest('Windows global hotkeys are only available on Windows')

from ctypes import addressof
from ctypes.wintypes import MSG
from unittest.mock import Mock, patch

from PyQt5.QtCore import Qt

from fman.impl.global_hotkey import (
	GlobalHotkey, MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, parse_hotkey,
)


class ParseHotkeyTest(unittest.TestCase):
	def test_supported_chords(self):
		self.assertEqual((MOD_CONTROL | MOD_ALT, ord('F')), parse_hotkey('Ctrl+Alt+F'))
		self.assertEqual((MOD_WIN | MOD_ALT, ord('7')), parse_hotkey('Win+Alt+7'))
		self.assertEqual((MOD_CONTROL | MOD_SHIFT, 0x70), parse_hotkey('Ctrl+Shift+F1'))
		self.assertEqual((MOD_CONTROL, 0x25), parse_hotkey('Ctrl+Left'))

	def test_empty_setting(self):
		self.assertIsNone(parse_hotkey(''))

	def test_unsupported_keys_and_modifiers(self):
		for chord in ('Ctrl+Alt+§', 'Ctrl+Alt+Media Play', 'Ctrl+Alt+CapsLock'):
			with self.subTest(chord=chord), self.assertRaises(ValueError):
				parse_hotkey(chord)
		with patch(
			'fman.impl.global_hotkey.parse_chord',
			return_value=(Qt.Key_F, Qt.KeypadModifier),
		), self.assertRaises(ValueError):
			parse_hotkey('Ctrl+F')


class GlobalHotkeyTest(unittest.TestCase):
	def setUp(self):
		self.callback = Mock()
		self.status = Mock()
		self.hotkey = GlobalHotkey(self.callback, self.status)

	def test_empty_setting_does_not_register(self):
		with patch('fman.impl.global_hotkey.windll.user32.RegisterHotKey') as register:
			self.assertIsNone(self.hotkey.register(''))
		register.assert_not_called()

	def test_invalid_key_reports_status_without_registering(self):
		with patch('fman.impl.global_hotkey.windll.user32.RegisterHotKey') as register:
			self.hotkey.register('Ctrl+Alt+§')
		register.assert_not_called()
		self.status.assert_called_once_with('Invalid global hotkey: Ctrl+Alt+§')

	def test_registration_failure_reports_already_registered(self):
		with patch(
			'fman.impl.global_hotkey.windll.user32.RegisterHotKey', return_value=0
		):
			self.hotkey.register('Ctrl+Alt+F')
		self.status.assert_called_once_with(
			'Global hotkey is already in use: Ctrl+Alt+F'
		)

	def test_unregister_only_unregisters_registered_hotkey(self):
		with patch(
			'fman.impl.global_hotkey.windll.user32.RegisterHotKey', return_value=1
		), patch(
			'fman.impl.global_hotkey.windll.user32.UnregisterHotKey'
		) as unregister:
			self.hotkey.register('Ctrl+Alt+F')
			self.hotkey.unregister()
			unregister.assert_called_once()
			unregister.reset_mock()
			self.hotkey.unregister()
			unregister.assert_not_called()

	def test_native_event_dispatch_accepts_both_qt_message_types(self):
		msg = MSG()
		msg.message = 0x0312  # WM_HOTKEY
		msg.wParam = 1
		with patch('fman.impl.global_hotkey.QTimer.singleShot') as single_shot:
			for event_type in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
				self.assertEqual(
					(True, 0),
					self.hotkey.nativeEventFilter(event_type, addressof(msg)),
				)
		self.assertEqual(2, single_shot.call_count)
		single_shot.assert_called_with(0, self.callback)

	def test_unrelated_messages_are_not_consumed(self):
		msg = MSG()
		msg.message = 0x1234
		self.assertEqual(
			(False, 0),
			self.hotkey.nativeEventFilter(b'windows_generic_MSG', addressof(msg)),
		)
		self.assertEqual(
			(False, 0),
			self.hotkey.nativeEventFilter(b'windows_other_MSG', addressof(msg)),
		)


if __name__ == '__main__':
	unittest.main()
