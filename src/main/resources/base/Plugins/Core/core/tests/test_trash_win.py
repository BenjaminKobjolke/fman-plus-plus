import os
import tempfile
from unittest import TestCase

from fman import PLATFORM, Task


class TrashWindowsTest(TestCase):
	def setUp(self):
		if PLATFORM != 'Windows':
			self.skipTest('Windows only')
		try:
			import pythoncom
			from win32com.shell import shell, shellcon
		except ImportError:
			self.skipTest('pywin32 is not installed')
		from core import trash_win
		self.trash_win = trash_win
		self.shell = shell
		self.shellcon = shellcon

	def test_canceled_sink_aborts_before_recycle(self):
		task = _Task(canceled=True)
		sink = self.trash_win.ProgressSink(task)
		with self.assertRaises(self.trash_win.COMException) as error:
			sink.PreDeleteItem(
				self.shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE, None
			)
		self.assertEqual(self.trash_win.E_ABORT, error.exception.hresult)

	def test_sink_shows_waiting_text_and_preserves_recycle_check(self):
		task = _Task()
		sink = self.trash_win.ProgressSink(task)
		result = sink.PreDeleteItem(
			self.shellcon.TSF_DELETE_RECYCLE_IF_POSSIBLE, None
		)
		self.assertEqual(0, result)
		self.assertEqual(
			self.trash_win.WAITING_TEXT, task.cancel_text
		)

	def test_canceled_shell_operation_leaves_folder_in_place(self):
		with tempfile.TemporaryDirectory() as folder:
			with open(os.path.join(folder, 'file.txt'), 'w') as file:
				file.write('content')
			with self.assertRaises(Task.Canceled):
				self.trash_win.send_to_trash(folder, _Task(canceled=True))
			self.assertTrue(os.path.isdir(folder))


class _Task:
	Canceled = Task.Canceled

	def __init__(self, canceled=False):
		self.canceled = canceled
		self.cancel_text = None
	def check_canceled(self):
		if self.canceled:
			raise self.Canceled()
	def set_cancel_text(self, text):
		self.cancel_text = text
