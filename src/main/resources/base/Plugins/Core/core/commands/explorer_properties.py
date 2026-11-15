from fman import DirectoryPaneCommand, show_alert
from fman.fs import resolve
from fman.url import splitscheme, as_human_readable, basename, dirname
from .properties_placement import PropertiesPlacer

import ctypes.wintypes
import os
import re

class ShowExplorerProperties(DirectoryPaneCommand):

	aliases = 'Properties',
	usable_in_viewer = True

	def __call__(self):
		scheme = splitscheme(self.pane.get_path())[0]
		if scheme not in ('file://', 'drives://', 'network://'):
			show_alert(
				'Sorry, showing the properties of %s files is not '
				'yet supported.' % scheme
			)
		else:
			action = self._get_action()
			if action:
				action()
	def _get_action(self):
		file_under_cursor = self.pane.get_file_under_cursor()
		selected_files = self.pane.get_selected_files()
		chosen_files = selected_files or \
		               ([file_under_cursor] if file_under_cursor else [])
		location = self.pane.get_path()
		scheme, path = splitscheme(location)
		if scheme == 'file://':
			if file_under_cursor is None:
				# Either we're in an empty folder, or the user
				# right-clicked inside a directory.
				if self._is_drive(path):
					return lambda: _show_drive_properties(self.pane, path)
				else:
					dir_ = as_human_readable(dirname(location))
					filenames = [basename(location)]
			else:
				dir_ = as_human_readable(location)
				filenames = [basename(f) for f in chosen_files]
			return lambda: _show_file_properties(self.pane, dir_, filenames)
		elif scheme == 'drives://':
			if file_under_cursor is None:
				# This usually happens when the user right-clicked in the drive
				# overview (but not _on_ a drive).
				return None
			drive = splitscheme(file_under_cursor)[1]
			if self._is_drive(drive):
				return lambda: _show_drive_properties(self.pane, drive)
		elif scheme == 'network://':
			# We check `path` because when it's empty, we're at the
			# overview of network locations. Servers don't have a Properties
			# dialog. So we can't do anything there.
			if path:
				for f in chosen_files:
					try:
						f_fileurl = resolve(f)
					except OSError:
						continue
					if splitscheme(f_fileurl)[0] != 'file://':
						# Sanity check. We don't actually expect this.
						continue
					dir_ = as_human_readable(dirname(f_fileurl))
					break
				else:
					return
				filenames = [basename(f) for f in chosen_files]
				return lambda: _show_file_properties(self.pane, dir_, filenames)
	def is_visible(self):
		return bool(self._get_action())
	def _is_drive(self, path):
		return re.match('^[A-Z]:$', path)

def _show_file_properties(pane, dir_, filenames):
	placer = PropertiesPlacer(pane, expected=len(filenames))
	# ShellExecuteEx opens one dialog per file, so multi-select shows a dialog
	# per selected file. Combining them into a single dialog would need
	# SHMultiFileProperties, which isn't available in this pywin32 build.
	for filename in filenames:
		_show_properties_via_shellexecute(os.path.join(dir_, filename))
	placer.watch()

def _show_drive_properties(pane, drive_nobackslash):
	placer = PropertiesPlacer(pane, expected=1)
	_show_properties_via_shellexecute(drive_nobackslash + '\\')
	placer.watch()

def _show_properties_via_shellexecute(path):
	# Invoke the shell "properties" verb through ShellExecuteEx. We deliberately
	# avoid the IContextMenu.InvokeCommand("properties") route: invoked with a
	# null owner hwnd on fman's Qt main thread it access-violates and crashes
	# the whole app.
	sei = SHELLEXECUTEINFO()
	sei.cbSize = ctypes.sizeof(sei)
	sei.fMask = _SEE_MASK_NOCLOSEPROCESS | _SEE_MASK_INVOKEIDLIST
	sei.lpVerb = "properties"
	sei.lpFile = path
	sei.nShow = 1
	ShellExecuteEx(ctypes.byref(sei))

_SEE_MASK_NOCLOSEPROCESS = 0x00000040
_SEE_MASK_INVOKEIDLIST = 0x0000000C

class SHELLEXECUTEINFO(ctypes.Structure):
	_fields_ = (
		("cbSize", ctypes.wintypes.DWORD),
		("fMask", ctypes.c_ulong),
		("hwnd", ctypes.wintypes.HANDLE),
		("lpVerb", ctypes.c_wchar_p),
		("lpFile", ctypes.c_wchar_p),
		("lpParameters", ctypes.c_char_p),
		("lpDirectory", ctypes.c_char_p),
		("nShow", ctypes.c_int),
		("hInstApp", ctypes.wintypes.HINSTANCE),
		("lpIDList", ctypes.c_void_p),
		("lpClass", ctypes.c_char_p),
		("hKeyClass", ctypes.wintypes.HKEY),
		("dwHotKey", ctypes.wintypes.DWORD),
		("hIconOrMonitor", ctypes.wintypes.HANDLE),
		("hProcess", ctypes.wintypes.HANDLE),
	)

ShellExecuteEx = ctypes.windll.shell32.ShellExecuteExW
ShellExecuteEx.restype = ctypes.wintypes.BOOL
