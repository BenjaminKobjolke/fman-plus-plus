import ctypes
from ctypes import addressof
from fman.impl.shell_change_notices import ShellChangeBatch, \
	ShellChangeListener, _CHANGE_MESSAGE, _MSG, _ShellChangeNotificationSource, \
	_paths_from_notification
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock, patch


_APP = QApplication.instance() or QApplication([])


class PathsFromNotificationTest(TestCase):

	def test_reads_paths_from_the_array_returned_by_shell_lock(self):
		pidl_a = 0x1234
		lock_handle = 0x5678
		event_id = 42
		pidls = (ctypes.c_void_p * 2)(pidl_a, None)
		shell32 = Mock()

		def lock_notification(notification, event, pppidl, event_id_pointer):
			pointer_to_pidls = ctypes.cast(
				ctypes.byref(pppidl._obj),
				ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
			)
			pointer_to_pidls[0] = ctypes.cast(
				ctypes.addressof(pidls), ctypes.POINTER(ctypes.c_void_p)
			)
			event_id_pointer._obj.value = event_id
			return lock_handle

		def get_path(pidl, path):
			path.value = r'C:\work\one.txt'
			return 1

		shell32.SHChangeNotification_Lock.side_effect = lock_notification
		shell32.SHGetPathFromIDListW.side_effect = get_path

		self.assertEqual(
			((r'C:\work\one.txt',), event_id),
			_paths_from_notification(shell32, 123, 456)
		)
		shell32.SHGetPathFromIDListW.assert_called_once()
		self.assertEqual(
			pidl_a, shell32.SHGetPathFromIDListW.call_args.args[0]
		)
		shell32.SHChangeNotification_Unlock.assert_called_once_with(lock_handle)

	def test_does_not_unlock_when_shell_lock_fails(self):
		shell32 = Mock()
		shell32.SHChangeNotification_Lock.return_value = 0

		self.assertEqual(((), 0), _paths_from_notification(shell32, 123, 456))
		shell32.SHChangeNotification_Unlock.assert_not_called()


class ShellChangeBatchTest(TestCase):

	def test_batches_changed_items_by_parent_folder(self):
		batch = ShellChangeBatch()

		batch.add(r'C:\work\one.txt')
		batch.add(r'C:\work\two.txt')
		batch.add(r'C:\other\three.txt')

		self.assertEqual(
			('file://C:/other', 'file://C:/work'), batch.flush()
		)
		self.assertEqual((), batch.flush())

	def test_updated_directory_refreshes_itself_and_its_parent(self):
		batch = ShellChangeBatch()

		batch.add(r'C:\work\subfolder', include_path=True)

		self.assertEqual(
			('file://C:/work', 'file://C:/work/subfolder'), batch.flush()
		)

	def test_flush_clears_a_batch_before_the_next_notice(self):
		batch = ShellChangeBatch()

		batch.add(r'C:\work\one.txt')
		self.assertEqual(('file://C:/work',), batch.flush())
		batch.add(r'C:\work\two.txt')

		self.assertEqual(('file://C:/work',), batch.flush())


class ShellChangeListenerTest(TestCase):

	def test_debounced_flush_invalidates_icons_and_reloads_matching_panes(self):
		pane = Mock()
		pane.get_location.return_value = 'file://C:/WORK'
		other_pane = Mock()
		other_pane.get_location.return_value = 'file://C:/elsewhere'
		window = Mock()
		window.get_panes.return_value = [pane, other_pane]
		source = _NotificationSource()
		listener = ShellChangeListener(window, lambda: True, source)

		try:
			source.notify([r'C:\work\one.txt', r'C:\work\two.txt'])
			self.assertEqual(300, listener._timer.interval())
			with patch('fman.impl.shell_change_notices.invalidate_icons') \
				as invalidate_icons:
				listener._flush()
			invalidate_icons.assert_called_once_with()
			pane.reload.assert_called_once_with()
			other_pane.reload.assert_not_called()
		finally:
			listener.close()

	def test_disabled_overlays_do_not_refresh_panes(self):
		pane = Mock()
		pane.get_location.return_value = 'file://C:/work'
		window = Mock()
		window.get_panes.return_value = [pane]
		listener = ShellChangeListener(
			window, lambda: False, _NotificationSource()
		)

		try:
			listener._on_changed_paths([r'C:\work\one.txt'])
			with patch('fman.impl.shell_change_notices.invalidate_icons') \
				as invalidate_icons:
				listener._flush()
			invalidate_icons.assert_not_called()
			pane.reload.assert_not_called()
		finally:
			listener.close()


class ShellChangeNotificationSourceTest(TestCase):
	"""PyQt calls nativeEventFilter(event_type, message) and expects (bool, int)."""

	def setUp(self):
		self.callback = Mock()
		self.source = _ShellChangeNotificationSource(self.callback)

	def tearDown(self):
		self.source.close()

	def test_ignores_other_event_types(self):
		msg = _MSG(self.source._hwnd, _CHANGE_MESSAGE, 0, 0)
		self.assertEqual(
			(False, 0),
			self.source.nativeEventFilter(b'windows_other_MSG', addressof(msg))
		)
		self.callback.assert_not_called()

	def test_ignores_other_messages(self):
		msg = _MSG(self.source._hwnd, _CHANGE_MESSAGE + 1, 0, 0)
		self.assertEqual(
			(False, 0),
			self.source.nativeEventFilter(b'windows_generic_MSG', addressof(msg))
		)
		self.callback.assert_not_called()

	def test_reports_changed_paths_of_its_own_message(self):
		msg = _MSG(self.source._hwnd, _CHANGE_MESSAGE, 0, 0)
		with patch(
			'fman.impl.shell_change_notices._paths_from_notification',
			return_value=([r'C:\work\one.txt'], 4)
		):
			result = self.source.nativeEventFilter(
				b'windows_generic_MSG', addressof(msg)
			)
		self.assertEqual((False, 0), result)
		self.callback.assert_called_once_with([r'C:\work\one.txt'], 4)


class _NotificationSource:
	def set_callback(self, callback):
		self._callback = callback

	def notify(self, paths, event_id=0):
		self._callback(paths, event_id)

	def close(self):
		pass
