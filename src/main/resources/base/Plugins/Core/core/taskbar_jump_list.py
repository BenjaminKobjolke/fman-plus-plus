"""Build Windows taskbar entries from Core's saved folder pins.

BeginList must be called without an IID: pywin32 crashes when one is passed.
The list uses the process taskbar identity so grouped fman windows share it.
Windows reports entries removed by the user, which must be dropped before
AppendCategory or the rebuild fails.
"""
import os
import subprocess
import sys

from fbs_runtime.application_context import is_frozen
from fman import log

from core.settings import SETTINGS_FILE, get_setting, save_setting


SETTING_KEY = 'taskbar_pinned_folders'
CATEGORY_TITLE = 'Pinned folders'
_APP_ID_FOR_TESTS = None


def get_pinned_folders():
	return get_setting(SETTINGS_FILE, SETTING_KEY, [])


def save_pinned_folders(paths):
	save_setting(SETTINGS_FILE, SETTING_KEY, paths or None)


def launch_arguments(path):
	arguments = [path]
	if not is_frozen():
		arguments.insert(0, sys.argv[0])
	command_line = subprocess.list2cmdline(arguments)
	# list2cmdline leaves a bare drive root unquoted. In a shell link, the
	# closing quote would then be consumed as part of the root argument.
	if path.endswith('\\') and not command_line.endswith('"'):
		path_argument = '"' + path[:-1] + '\\\\' + '"'
		prefix = subprocess.list2cmdline(arguments[:-1])
		return (prefix + ' ' if prefix else '') + path_argument
	return command_line


def _normalized_path(path):
	return os.path.normcase(os.path.normpath(path))


def surviving_paths(saved, removed):
	removed_paths = {_normalized_path(path) for path in removed}
	return [
		path for path in saved
		if _normalized_path(path) not in removed_paths
	]


def _removed_paths(removed, shell):
	paths = []
	for index in range(removed.GetCount()):
		link = removed.GetAt(index, shell.IID_IShellLink)
		paths.append(link.GetDescription())
	return paths


def _make_shell_link(path, pythoncom, shell, propsys, pscon):
	link = pythoncom.CoCreateInstance(
		shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER,
		shell.IID_IShellLink
	)
	link.SetPath(sys.executable)
	link.SetArguments(launch_arguments(path))
	link.SetDescription(path)
	icon_path = os.path.join(
		os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'shell32.dll'
	)
	link.SetIconLocation(icon_path, 3)
	property_store = link.QueryInterface(propsys.IID_IPropertyStore)
	property_store.SetValue(
		pscon.PKEY_Title,
		propsys.PROPVARIANTType(
			os.path.basename(path.rstrip('\\/')) or path
		)
	)
	property_store.Commit()
	return link


def rebuild(paths):
	"""Replace the custom jump-list category, preserving user removals."""
	import pythoncom
	import pywintypes
	from win32com.propsys import propsys, pscon
	from win32com.shell import shell

	initialized = False
	destination_list = None
	list_begun = False
	try:
		pythoncom.CoInitialize()
		initialized = True
		destination_list = pythoncom.CoCreateInstance(
			shell.CLSID_DestinationList, None,
			pythoncom.CLSCTX_INPROC_SERVER,
			shell.IID_ICustomDestinationList
		)
		if _APP_ID_FOR_TESTS is not None:
			destination_list.SetAppID(_APP_ID_FOR_TESTS)
		_, removed = destination_list.BeginList()
		list_begun = True
		survivors = surviving_paths(paths, _removed_paths(removed, shell))
		if not survivors:
			destination_list.CommitList()
			list_begun = False
			return survivors

		collection = pythoncom.CoCreateInstance(
			shell.CLSID_EnumerableObjectCollection, None,
			pythoncom.CLSCTX_INPROC_SERVER,
			shell.IID_IObjectCollection
		)
		for path in survivors:
			collection.AddObject(
				_make_shell_link(path, pythoncom, shell, propsys, pscon)
			)
		objects = collection.QueryInterface(shell.IID_IObjectArray)
		destination_list.AppendCategory(CATEGORY_TITLE, objects)
		destination_list.CommitList()
		list_begun = False
		return survivors
	except (pywintypes.com_error, OSError) as error:
		if list_begun:
			try:
				destination_list.AbortList()
			except (pywintypes.com_error, OSError):
				pass
		log('taskbar_jump_list.rebuild', 'Could not update Windows jump list:', error)
		return paths
	finally:
		if initialized:
			pythoncom.CoUninitialize()
