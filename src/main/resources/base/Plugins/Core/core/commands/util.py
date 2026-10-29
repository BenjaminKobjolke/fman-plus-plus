from core import elevation
from fman import PLATFORM, show_alert, translate
from fman.localization_keys import (
	COULD_NOT_CREATE as COULD_NOT_CREATE_KEY,
	COULD_NOT_READ as COULD_NOT_READ_KEY,
	NO_SELECTION as NO_SELECTION_KEY,
	SHORTCUT_TARGET_MISSING as SHORTCUT_TARGET_MISSING_KEY,
)
from fman.fs import is_dir
from fman.url import as_human_readable, splitscheme
from getpass import getuser
from os.path import expanduser
from PyQt5.QtCore import QFileInfo

import os

# The two messages several unrelated commands answer with. They are one
# string each rather than one literal per command so the wording cannot
# drift between the command that deletes and the command that packs.
NO_SELECTION = translate(NO_SELECTION_KEY)
CANNOT_READ = translate(COULD_NOT_READ_KEY)
CANNOT_CREATE = translate(COULD_NOT_CREATE_KEY)
SHORTCUT_TARGET_MISSING = translate(SHORTCUT_TARGET_MISSING_KEY)

SHORTCUT_SUFFIX = '.lnk'

if PLATFORM == 'Windows':
	import winreg

# Where Explorer records the current location of the per-user folders. The
# sibling key 'User Shell Folders' holds the same paths unexpanded
# (%USERPROFILE% and friends); this one is already resolved, so no
# expandvars() is needed.
_SHELL_FOLDERS_KEY = \
	r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
# Downloads is the odd one out: it has no legacy name in the registry, only its
# known-folder GUID. Desktop and Documents ('Personal') predate that scheme.
_DOWNLOADS = '{374DE290-123F-4565-9164-39C4925E467B}'

def _query_shell_folder(reg_name):
	try:
		with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SHELL_FOLDERS_KEY) as key:
			return winreg.QueryValueEx(key, reg_name)[0]
	except OSError:
		return None

def shell_folder(reg_name, fallback):
	# ~/Desktop is a guess, not a fact: OneDrive's "Back up your folders"
	# relocates Desktop, Documents and Downloads into ~/OneDrive, and only the
	# registry knows where they went. Fall back to the guess off Windows, or
	# when the value is missing.
	if PLATFORM == 'Windows':
		result = _query_shell_folder(reg_name)
		if result:
			return result
	return expanduser(fallback)

def get_home():
	return expanduser('~')

def get_desktop():
	return shell_folder('Desktop', '~/Desktop')

def get_documents():
	return shell_folder('Personal', '~/Documents')

def get_downloads():
	return shell_folder(_DOWNLOADS, '~/Downloads')

def get_well_known_dirs():
	# The everyday four, as {path: name}. Both GoTo's suggestion pool and the
	# Go to X palette commands in core/commands/places.py resolve them through
	# here, so there is one answer to "where is Desktop" per machine. The names
	# make them searchable in GoTo: the home directory shows as '~', which
	# nothing you would type to find it has a letter in common with.
	return {
		get_home(): 'Home',
		get_desktop(): 'Desktop',
		get_documents(): 'Documents',
		get_downloads(): 'Downloads'
	}

def get_program_files():
	return os.environ.get('PROGRAMW6432', r'C:\Program Files')

def get_program_files_x86():
	return os.environ.get('PROGRAMFILES', r'C:\Program Files (x86)')

def get_user():
	try:
		return getuser()
	except Exception:
		return os.path.basename(expanduser('~'))

def is_hidden(file_path):
	return QFileInfo(file_path).isHidden()

def is_file_url(url):
	# Lives here rather than next to any one caller: the commands that only
	# work on local files are spread over several modules (opening, transfer,
	# window, external), and none of them may import another without making
	# core/commands/__init__.py's star imports circular.
	return splitscheme(url)[0] == 'file://'

def is_shortcut(path_or_url):
	# Lower-cased because Windows file names are case-insensitive: Explorer
	# happily creates X.LNK.
	return path_or_url.lower().endswith(SHORTCUT_SUFFIX)

def shortcut_target(path):
	# Windows only. '' when the shortcut has no file system target (advertised
	# MSI shortcuts, shell-namespace targets) or cannot be read at all. Shared
	# by Enter (core/commands/opening.py) and follow_shortcut
	# (core/commands/navigation.py), which may not import each other.
	import win32com.client
	from pythoncom import com_error
	try:
		shell = win32com.client.Dispatch('WScript.Shell')
		return shell.CreateShortCut(path).TargetPath
	except com_error:
		return ''

def chosen_files(command):
	# The selection a "do this to the chosen files" command starts from.
	# Alerts and returns [] when there is none, so each caller is one `if
	# not files: return` instead of its own copy of the guard.
	files = command.get_chosen_files()
	if not files:
		show_alert(NO_SELECTION)
	return files

def create_as_admin(url, is_dir, error):
	# A UAC prompt can only help for local paths; elsewhere report the error
	# from the plugin file system instead of trying an unrelated shell operation.
	if not is_file_url(url):
		show_alert(CANNOT_CREATE % (as_human_readable(url), error))
		return False
	# For local paths, retry with a UAC prompt. The user may decline it.
	if elevation.create(url, is_dir=is_dir):
		return True
	show_alert(
		'You do not have enough permissions to create %s.'
		% as_human_readable(url)
	)
	return False

def is_dir_checked(url, alert=show_alert):
	# is_dir(...), except that a file system which cannot answer at all
	# (a disconnected share, a permission error) alerts and yields None
	# rather than raising - callers here want to stop, not to crash. None
	# and False are different answers, so test with `is None`.
	try:
		return is_dir(url)
	except OSError as e:
		alert(CANNOT_READ % (as_human_readable(url), e))
		return None

def require_file_url(url, gerund):
	# The commands that hand a file to another program can only do so for a
	# real path on disk. They all point the user at the plugin API in the
	# same breath, so the hint lives here rather than being retyped per
	# command. `gerund` names the action: 'Opening', 'Editing'.
	scheme = splitscheme(url)[0]
	if scheme == 'file://':
		return True
	show_alert(
		'%s files from %s is not supported. If you are a plugin developer, '
		'you can implement this with DirectoryPaneListener#on_command(...).'
		% (gerund, scheme)
	)
	return False

def get_opposite_pane(pane):
	# Same reason as is_file_url above: the panes' "the other one" lookup is
	# needed by commands in pane_view, transfer and opening, and none of those
	# may import another without making core/commands/__init__.py's star
	# imports circular.
	panes = pane.window.get_panes()
	return panes[(panes.index(pane) + 1) % len(panes)]
