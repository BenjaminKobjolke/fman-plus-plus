import unittest
from unittest.mock import Mock

from fbs_runtime.platform import is_windows

if not is_windows():
	raise unittest.SkipTest('Virtual file drops are only available on Windows')

from fman.impl import virtual_file_drop


class TestDropTargetProxy(unittest.TestCase):
	def setUp(self):
		self.inner = Mock()
		self.proxy = virtual_file_drop._DropTargetProxy(self.inner)

	def test_forwards_all_drop_target_calls(self):
		data_object = object()
		calls = {
			'DragEnter': (data_object, 1, 2, 3),
			'DragOver': (1, 2, 3),
			'DragLeave': (),
			'Drop': (data_object, 1, 2, 3)
		}
		for method, args in calls.items():
			getattr(self.inner, method).return_value = method
			self.assertEqual(method, getattr(self.proxy, method)(*args))
			getattr(self.inner, method).assert_called_with(*args)

	def test_keeps_data_object_until_drop_finishes(self):
		data_object = object()
		self.inner.Drop.side_effect = lambda *args: self.assertIs(
			data_object, virtual_file_drop.current_data_object())
		self.proxy.DragEnter(data_object, 0, None, 0)
		self.assertIs(data_object, virtual_file_drop.current_data_object())
		self.proxy.Drop(data_object, 0, None, 0)
		self.assertIsNone(virtual_file_drop.current_data_object())

	def test_clears_data_object_after_leave_and_failed_drop(self):
		data_object = object()
		self.proxy.DragEnter(data_object, 0, None, 0)
		self.proxy.DragLeave()
		self.assertIsNone(virtual_file_drop.current_data_object())

		self.proxy.DragEnter(data_object, 0, None, 0)
		self.inner.Drop.side_effect = RuntimeError('drop failed')
		with self.assertRaisesRegex(RuntimeError, 'drop failed'):
			self.proxy.Drop(data_object, 0, None, 0)
		self.assertIsNone(virtual_file_drop.current_data_object())
