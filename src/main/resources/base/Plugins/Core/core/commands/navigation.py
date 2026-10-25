"""Moving around: the cursor, the selection, the directory stack, volumes.

`go_up` is a module-level function rather than only `GoUp.__call__` because
`HistoryListener` reuses it - going back to the parent directory has to place
the cursor on the directory just left, which plain `set_path` does not do.
"""
from core.commands.util import is_file_url, is_shortcut, shortcut_target, \
	SHORTCUT_TARGET_MISSING
from fman import DirectoryPaneCommand, DirectoryPaneListener, PLATFORM, \
	show_alert
from fman.fs import iterdir
from fman.impl.util import get_user
from fman.url import as_human_readable, as_url, dirname, join, splitscheme
from pathlib import PurePath

import os
import os.path

__all__ = [
	'Deselect', 'GoBack', 'GoForward', 'GoUp', 'History', 'HistoryListener',
	'InvertSelection', 'MoveCursorDown', 'MoveCursorEnd', 'MoveCursorHome',
	'MoveCursorPageDown', 'MoveCursorPageUp', 'MoveCursorUp', 'OpenInLeftPane',
	'OpenInRightPane', 'SelectAll', 'ShowVolumes', 'ToggleSelection', 'go_up'
]
if PLATFORM == 'Windows':
	__all__ += ['FollowShortcut', 'GoToRootOfCurrentDrive']

class MoveCursorDown(DirectoryPaneCommand):
	def __call__(self, toggle_selection=False):
		self.pane.move_cursor_down(toggle_selection)

class MoveCursorUp(DirectoryPaneCommand):
	def __call__(self, toggle_selection=False):
		self.pane.move_cursor_up(toggle_selection)

class MoveCursorHome(DirectoryPaneCommand):
	def __call__(self, toggle_selection=False):
		self.pane.move_cursor_home(toggle_selection)

class MoveCursorEnd(DirectoryPaneCommand):
	def __call__(self, toggle_selection=False):
		self.pane.move_cursor_end(toggle_selection)

class MoveCursorPageUp(DirectoryPaneCommand):
	def __call__(self, toggle_selection=False):
		self.pane.move_cursor_page_up(toggle_selection)

class MoveCursorPageDown(DirectoryPaneCommand):
	def __call__(self, toggle_selection=False):
		self.pane.move_cursor_page_down(toggle_selection)

class ToggleSelection(DirectoryPaneCommand):
	def __call__(self):
		file_under_cursor = self.pane.get_file_under_cursor()
		if file_under_cursor:
			self.pane.toggle_selection(file_under_cursor)

class GoUp(DirectoryPaneCommand):

	aliases = ('Go up',)

	def __call__(self):
		go_up(self.pane)

def go_up(pane):
	path_before = pane.get_path()
	def callback():
		path_now = pane.get_path()
		# Only move the cursor if we actually changed directories; For
		# instance, we don't want to move the cursor if the user presses
		# Backspace while at drives:// and the cursor is already at
		# drives://C:
		if path_now != path_before:
			# Consider: The user is in zip:///Temp.zip and invokes GoUp.
			# This takes us to file:///. We want to place the cursor at
			# file:///Temp.zip. "Switch" schemes to make this happen:
			cursor_dest = splitscheme(path_now)[0] + \
						  splitscheme(path_before)[1]
			try:
				pane.place_cursor_at(cursor_dest)
			except ValueError:
				pane.move_cursor_home()
	parent_dir = dirname(path_before)
	try:
		pane.set_path(parent_dir, callback)
	except FileNotFoundError:
		# This for instance happens when the user pressed backspace when at
		# file:/// on Unix.
		pass

class SelectAll(DirectoryPaneCommand):
	def __call__(self):
		self.pane.select_all()

class Deselect(DirectoryPaneCommand):
	def __call__(self):
		self.pane.clear_selection()

class InvertSelection(DirectoryPaneCommand):
	def __call__(self, *args, **kwargs):
		url = self.pane.get_path()
		all_files = (join(url, fname) for fname in iterdir(url))
		to_deselect = set(self.pane.get_selected_files())
		to_select = (f for f in all_files if f not in to_deselect)
		self.pane.deselect(to_deselect)
		self.pane.select(to_select)

class _OpenInPaneCommand(DirectoryPaneCommand):
	def is_visible(self):
		return len(self.pane.window.get_panes()) > 1
	def __call__(self):
		panes = self.pane.window.get_panes()
		num_panes = len(panes)
		if num_panes < 2:
			return
		this_pane = panes.index(self.pane)
		source_pane = panes[self.get_source_pane(this_pane, num_panes)]
		if source_pane is self.pane:
			to_open = source_pane.get_file_under_cursor() or \
					  source_pane.get_path()
		else:
			# This for instance happens when the right pane is active and the
			# user asks to "open in the right pane". The source pane in this
			# case is the left pane. The cursor in the left pane is not visible
			# (because the right pane is active) - but it still exists and might
			# be over a directory! If we opened the directory under the cursor,
			# we would thus open a subdirectory of the left pane. That's not
			# what we want. We want to open the directory of the left pane:
			to_open = source_pane.get_path()
		dest_pane = panes[self.get_destination_pane(this_pane, num_panes)]
		dest_pane.run_command('open_directory', {'url': to_open})
	def get_source_pane(self, this_pane, num_panes):
		raise NotImplementedError()
	def get_destination_pane(self, this_pane, num_panes):
		raise NotImplementedError()

class OpenInRightPane(_OpenInPaneCommand):
	def get_source_pane(self, this_pane, num_panes):
		if this_pane == num_panes - 1:
			return this_pane - 1
		return this_pane
	def get_destination_pane(self, this_pane, num_panes):
		return min(this_pane + 1, num_panes - 1)

class OpenInLeftPane(_OpenInPaneCommand):
	def get_source_pane(self, this_pane, num_panes):
		if this_pane > 0:
			return this_pane
		return 1
	def get_destination_pane(self, this_pane, num_panes):
		return max(this_pane - 1, 0)

class ShowVolumes(DirectoryPaneCommand):

	aliases = ('Show volumes',)

	def __call__(self, pane_index=None):
		if pane_index is None:
			pane = self.pane
		else:
			panes = self.pane.window.get_panes()
			pane = panes[pane_index] if pane_index < len(panes) else self.pane
		def callback():
			pane.focus()
			pane.move_cursor_home()
		pane.set_path(_get_volumes_url(), callback=callback)

def _get_volumes_url():
	if PLATFORM == 'Mac':
		return 'file:///Volumes'
	elif PLATFORM == 'Windows':
		return 'drives://'
	elif PLATFORM == 'Linux':
		if os.path.isdir('/media'):
			contents = os.listdir('/media')
			user_name = get_user()
			if contents == [user_name]:
				return as_url(os.path.join('/media', user_name))
			else:
				return 'file:///media'
		else:
			return 'file:///mnt'
	else:
		raise NotImplementedError(PLATFORM)

class GoBack(DirectoryPaneCommand):
	def __call__(self):
		HistoryListener.INSTANCES[self.pane].go_back()

class GoForward(DirectoryPaneCommand):
	def __call__(self):
		HistoryListener.INSTANCES[self.pane].go_forward()

class HistoryListener(DirectoryPaneListener):

	INSTANCES = {}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._history = History()
		self.INSTANCES[self.pane] = self
	def go_back(self):
		self._go(self._history.go_back)
	def go_forward(self):
		self._go(self._history.go_forward)
	def _go(self, step):
		try:
			path = step()
		except ValueError:
			return
		self._navigate_to(path)
	def _navigate_to(self, path):
		if path == dirname(self.pane.get_path()):
			# Place the cursor at the current directory after going up:
			go_up(self.pane)
		else:
			self.pane.set_path(path)
	def on_path_changed(self):
		self._history.path_changed(self.pane.get_path())

class History:
	def __init__(self):
		self._paths = []
		self._curr_path = -1
		self._ignore_next_path_change = False
	def go_back(self):
		return self._go(-1)
	def go_forward(self):
		return self._go(+1)
	def _go(self, delta):
		# Raises rather than clamping: the caller has to tell "already at the
		# end" apart from "moved", and there is no path to navigate to.
		position = self._curr_path + delta
		if not 0 <= position < len(self._paths):
			raise ValueError()
		self._curr_path = position
		self._ignore_next_path_change = True
		return self._paths[position]
	def path_changed(self, path):
		if path == 'null://':
			return
		if self._ignore_next_path_change:
			self._ignore_next_path_change = False
			return
		self._curr_path += 1
		del self._paths[self._curr_path:]
		self._paths.append(path)

if PLATFORM == 'Windows':
	class GoToRootOfCurrentDrive(DirectoryPaneCommand):
		def __call__(self):
			url = self.pane.get_path()
			scheme = splitscheme(url)[0]
			if scheme == 'file://':
				dest = as_url(PurePath(as_human_readable(url)).anchor)
			else:
				dest = scheme
			try:
				self.pane.set_path(dest)
			except FileNotFoundError:
				pass

	class FollowShortcut(DirectoryPaneCommand):

		aliases = ('Follow shortcut',)

		def __call__(self):
			url = self.pane.get_file_under_cursor()
			target = shortcut_target(as_human_readable(url))
			if not target or not os.path.exists(target):
				show_alert(SHORTCUT_TARGET_MISSING % as_human_readable(url))
				return
			# open_directory rather than set_path: for a file target it opens
			# the parent and puts the cursor on the file.
			self.pane.run_command('open_directory', {'url': as_url(target)})
		def is_visible(self):
			url = self.pane.get_file_under_cursor()
			return bool(url) and is_file_url(url) and is_shortcut(url)
