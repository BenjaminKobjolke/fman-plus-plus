"""Windows Recycle Bin support with cancellation during the shell scan."""

from os import path as op
from platform import version

from fman import Task
from send2trash.compat import text_type
from send2trash.win.IFileOperationProgressSink import \
	FileOperationProgressSink as _FileOperationProgressSink
import pythoncom
import pywintypes
import winerror
from win32com.server.exception import COMException
from win32com.shell import shell, shellcon


WAITING_TEXT = (
	'Canceling... waiting for Windows to finish moving to the Recycle Bin.'
)
E_ABORT = winerror.E_ABORT


class ProgressSink(_FileOperationProgressSink):
	def __init__(self, task):
		self._task = task
		super().__init__()
	def PreDeleteItem(self, flags, item):
		try:
			self._task.check_canceled()
		except Task.Canceled:
			raise COMException(hresult=E_ABORT)
		self._task.set_cancel_text(WAITING_TEXT)
		return super().PreDeleteItem(flags, item)


def send_to_trash(path, task):
	path = text_type(path, 'mbcs') if not isinstance(path, text_type) else path
	path = op.abspath(path) if not op.isabs(path) else path
	path = path[4:] if path.startswith('\\\\?\\') else path
	pythoncom.CoInitialize()
	try:
		fileop = pythoncom.CoCreateInstance(
			shell.CLSID_FileOperation,
			None,
			pythoncom.CLSCTX_ALL,
			shell.IID_IFileOperation,
		)
		flags = shellcon.FOF_NOCONFIRMATION | shellcon.FOF_NOERRORUI | \
			shellcon.FOF_SILENT | shellcon.FOFX_EARLYFAILURE
		if int(version().split('.', 1)[0]) >= 8:
			flags |= 0x20000000 | 0x00080000
		else:
			flags |= shellcon.FOF_ALLOWUNDO
		fileop.SetOperationFlags(flags)
		item = shell.SHCreateItemFromParsingName(
			path, None, shell.IID_IShellItem
		)
		sink = pythoncom.WrapObject(
			ProgressSink(task), shell.IID_IFileOperationProgressSink
		)
		fileop.DeleteItem(item, sink)
		result = fileop.PerformOperations()
		aborted = fileop.GetAnyOperationsAborted()
		if result or aborted:
			if aborted:
				try:
					task.check_canceled()
				except Task.Canceled:
					raise
			raise OSError(None, None, path, result)
	except pywintypes.com_error as error:
		if error.hresult == E_ABORT:
			try:
				task.check_canceled()
			except Task.Canceled:
				raise
		raise OSError(None, error.strerror, path, error.hresult)
	finally:
		task.set_cancel_text(None)
		pythoncom.CoUninitialize()
