"""Showing and hiding dotfiles / hidden files in a directory pane.

"Toggle hidden files" flips the pane's filter; `InitHiddenFilesFilter`
installs it at startup because fman instantiates commands lazily and the
filter has to exist before the first pane is drawn. The per-pane choice
lives in 'Panes.json' so it survives a restart. Shown hidden entries are
faded unless `dim_hidden_files` in Core Settings.json is false.
The Windows commands change the file's hidden attribute; the toggle only
changes what the pane shows.
"""
from core.commands.util import chosen_files, is_file_url, is_hidden
from core.settings import get_setting, SETTINGS_FILE
from fman import DirectoryPaneCommand, DirectoryPaneListener, PLATFORM, \
	load_json, save_json, show_alert, show_status_message
from fman.fs import notify_file_changed, query
from fman.url import as_human_readable, splitscheme
from stat import FILE_ATTRIBUTE_HIDDEN

__all__ = ['InitHiddenFilesFilter', 'ToggleHiddenFiles']

if PLATFORM == 'Windows':
	__all__ += ['SetHiddenAttribute', 'ClearHiddenAttribute']
	import ctypes
	import ctypes.wintypes
	import os
	from stat import FILE_ATTRIBUTE_NORMAL

	_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
	_kernel32.SetFileAttributesW.argtypes = (
		ctypes.wintypes.LPCWSTR, ctypes.wintypes.DWORD
	)
	_kernel32.SetFileAttributesW.restype = ctypes.wintypes.BOOL

	def _set_hidden_attribute(path, hidden):
		attrs = os.lstat(path).st_file_attributes
		new = attrs | FILE_ATTRIBUTE_HIDDEN if hidden else \
			attrs & ~FILE_ATTRIBUTE_HIDDEN
		if new == attrs:
			return
		# FILE_ATTRIBUTE_NORMAL is only valid alone, and 0 is not a valid value.
		if not _kernel32.SetFileAttributesW(
			path, new or FILE_ATTRIBUTE_NORMAL
		):
			raise ctypes.WinError(ctypes.get_last_error())

_DIM_SETTING_KEY = 'dim_hidden_files'
_ATTRIBUTE_FAILED = 'Could not change the hidden attribute of:'

if PLATFORM == 'Windows':
	def _apply_hidden_attribute(command, hidden):
		files = chosen_files(command)
		if not files:
			return
		failed = []
		for url in files:
			name = as_human_readable(url)
			if not is_file_url(url):
				failed.append(name)
				continue
			try:
				_set_hidden_attribute(name, hidden)
			except OSError as error:
				failed.append('%s: %s' % (name, error.strerror or str(error)))
		notify_file_changed(command.pane.get_path())
		if failed:
			show_alert('%s\n%s' % (_ATTRIBUTE_FAILED, '\n'.join(failed)))
		else:
			verb = 'set on' if hidden else 'removed from'
			count = len(files)
			noun = 'file' if count == 1 else 'files'
			show_status_message(
				'Hidden attribute %s %d %s' % (verb, count, noun),
				timeout_secs=3
			)

class ToggleHiddenFiles(DirectoryPaneCommand):

	aliases = ('Toggle hidden files',)

	def __call__(self):
		_toggle_hidden_files(self.pane, not _is_showing_hidden_files(self.pane))

class InitHiddenFilesFilter(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# We need to do this somewhere when fman starts. We can't do it in the
		# __init__ of ToggleHiddenFiles, because fman instantiates commands
		# lazily.
		if not _is_showing_hidden_files(self.pane):
			_toggle_hidden_files(self.pane, False)
		else:
			_apply_dimmer(self.pane, True)

def _is_showing_hidden_files(pane):
	return _get_pane_info(pane)['show_hidden_files']

def _toggle_hidden_files(pane, value):
	if value:
		pane._remove_filter(_hidden_file_filter)
	else:
		pane._add_filter(_hidden_file_filter)
	_get_pane_info(pane)['show_hidden_files'] = value
	# Consider a scenario where the user:
	#  1. shows hidden files, then
	#  2. reloads plugins.
	# The second step reloads the settings. This reverts 'Panes.json' to the
	# version that was last saved. If we only relied on the save_on_quit
	# functionality of load_json(...), then the last saved version would be the
	# one when fman was last closed. But this does not reflect the fact that we
	# are now showing hidden files. So we flush Panes.json immediately to disk:
	save_json('Panes.json')
	# When we toggle hidden files again, this avoids an error caused by
	# `_remove_filter` being called for a non-active filter.
	_apply_dimmer(pane, value)

def _apply_dimmer(pane, showing_hidden):
	dimmer = _is_hidden_file if showing_hidden and get_setting(
		SETTINGS_FILE, _DIM_SETTING_KEY, True
	) else None
	pane._set_dimmer(dimmer)

def _get_pane_info(pane):
	settings = load_json('Panes.json', default=[])
	default = {'show_hidden_files': False}
	pane_index = pane.window.get_panes().index(pane)
	for _ in range(pane_index - len(settings) + 1):
		settings.append(default.copy())
	return settings[pane_index]

def _forget_pane_info(pane):
	settings = load_json('Panes.json', default=[])
	pane_index = pane.window.get_panes().index(pane)
	if pane_index < len(settings):
		del settings[pane_index]
		save_json('Panes.json')

def _hidden_file_filter(url):
	if PLATFORM == 'Mac' and url == 'file:///Volumes':
		return True
	scheme, path = splitscheme(url)
	if scheme != 'file://':
		return True
	if PLATFORM == 'Windows':
		# This filter runs in the GUI thread (Model#_record_files_main and
		# #update are @run_in_main_thread), so it must not perform an FS call of
		# its own: QFileInfo#isHidden() is uncached and froze the whole window
		# on network drives, where every call is a round trip. fman's own stat
		# is cached and has already been loaded for the Size/Modified columns.
		try:
			attrs = query(url, 'stat').st_file_attributes
		except OSError:
			return True
		return not attrs & FILE_ATTRIBUTE_HIDDEN
	return not is_hidden(path)

def _is_hidden_file(url):
	return not _hidden_file_filter(url)

if PLATFORM == 'Windows':
	class SetHiddenAttribute(DirectoryPaneCommand):
		aliases = ('Set hidden attribute',)

		def __call__(self):
			_apply_hidden_attribute(self, True)
		def is_visible(self):
			return is_file_url(self.pane.get_path())

	class ClearHiddenAttribute(DirectoryPaneCommand):
		aliases = ('Remove hidden attribute',)

		def __call__(self):
			_apply_hidden_attribute(self, False)
		def is_visible(self):
			return is_file_url(self.pane.get_path())
