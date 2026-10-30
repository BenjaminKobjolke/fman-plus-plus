"""Opening what the cursor is on - in fman, in a viewer, or in the OS.

`Open` deliberately delegates to the `open_directory` / `open_file` commands
instead of doing the work itself, so a plugin can override the default open
behaviour through DirectoryPaneListener#on_command(...).
"""
from core.commands.util import CANNOT_READ, get_opposite_pane, is_dir_checked, \
	is_file_url, is_shortcut, require_file_url, shortcut_target, NO_SELECTION
from core.commands.open_files_unix import (
	_open_local_files_linux, _open_local_files_mac,
)
from core.viewers import viewer_for
from fman import APP_NAME, DirectoryPaneCommand, DirectoryPaneListener, \
	NO, PLATFORM, YES, load_json, save_json, show_alert
from fman.fs import is_dir, resolve
from fman.url import as_human_readable, as_url, dirname, splitscheme

import errno
import os
import os.path

__all__ = [
	'Open', 'OpenDirectory', 'OpenFile', 'OpenListener', 'OpenOrView',
	'OpenSelectedFiles', 'ViewFile', 'ViewFileInOtherPane'
]

class Open(DirectoryPaneCommand):
	def __call__(self, url=None):
		if url is None:
			url = self.pane.get_file_under_cursor()
		if url:
			url_is_dir = is_dir_checked(url)
			if url_is_dir is None:
				return
			# Use `run_command` to delegate the actual opening. This makes it
			# possible for plugins to modify the default open behaviour by
			# implementing DirectoryPaneListener#on_command(...).
			if url_is_dir:
				if PLATFORM == 'Mac' and url.endswith('.app'):
					dialogs = load_json('Core Dialogs.json', default={})
					if not dialogs.get('open_app_hint_shown', False):
						show_alert(
							'Quick tip: Apps in macOS are directories. When '
							'you press '
							'<span style="color: white;">Enter</span>, ' +
							APP_NAME + ' therefore browses them. If you want to ' +
							'launch the app instead, press ' +
							'<span style="color: white;">Cmd+Enter</span>.'
						)
						dialogs['open_app_hint_shown'] = True
						save_json('Core Dialogs.json')
						return
				self.pane.run_command('open_directory', {'url': url})
			else:
				self.pane.run_command('open_file', {'url': url})
		else:
			show_alert(NO_SELECTION)

class OpenListener(DirectoryPaneListener):
	def on_doubleclicked(self, file_url):
		self.pane.run_command('open', {'url': file_url})

class OpenDirectory(DirectoryPaneCommand):
	def __call__(self, url):
		if PLATFORM == 'Windows':
			try:
				url_is_dir = is_dir(url)
			except PermissionError:
				from core.commands.network_shares import ShareLogin, log_in_to_share
				result = log_in_to_share(url)
				if result == ShareLogin.CONNECTED:
					try:
						url_is_dir = is_dir(url)
					except PermissionError:
						_show_access_denied(url)
						return
					except OSError as error:
						show_alert(CANNOT_READ % (as_human_readable(url), error))
						return
				elif result == ShareLogin.NOT_A_SHARE:
					_show_access_denied(url)
					return
				else:
					return
			except OSError as error:
				show_alert(CANNOT_READ % (as_human_readable(url), error))
				return
		else:
			url_is_dir = is_dir_checked(url)
			if url_is_dir is None:
				return
		if url_is_dir:
			try:
				self.pane.set_path(url, onerror=None)
			except PermissionError:
				if PLATFORM == 'Windows':
					from core.commands.network_shares import ShareLogin, log_in_to_share
					result = log_in_to_share(url)
					if result == ShareLogin.CONNECTED:
						try:
							self.pane.set_path(url, onerror=None)
						except PermissionError:
							_show_access_denied(url)
					elif result == ShareLogin.NOT_A_SHARE:
						_show_access_denied(url)
				else:
					_show_access_denied(url)
		else:
			def callback():
				try:
					self.pane.place_cursor_at(url)
				except ValueError:
					pass
			self.pane.set_path(dirname(url), callback=callback, onerror=None)
	def is_visible(self):
		return False

def _show_access_denied(url):
	show_alert('Access to "%s" was denied.' % as_human_readable(url))

class OpenFile(DirectoryPaneCommand):
	def __call__(self, url):
		_open_files([url], self.pane)
	def is_visible(self):
		return False

def _open_files(urls, pane):
	local_file_paths = []
	for url in urls:
		# On Windows, CMD can handle mapped drives Z:\ but not UNC paths
		# //192.168.0.2. If the former maps to the latter, then CMD fails to
		# run .bat files in that location. So only resolve if absolutely
		# necessary, i.e. when not a file:// URL:
		if not is_file_url(url):
			try:
				url = resolve(url)
			except FileNotFoundError:
				# No sense to try to open a file that does not exist.
				continue
			except OSError as e:
				# Not all OSErrors need prevent us from opening the file.
				# So only skip this file if it does not exist:
				if e.errno == errno.ENOENT:
					continue
		if not require_file_url(url, 'Opening'):
			return
		# Use as_human_readable(...) instead of the result from splitscheme(...)
		# above to get backslashes on Windows:
		local_file_paths.append(as_human_readable(url))
	_open_local_files(local_file_paths, pane)

def _open_local_files(paths, pane):
	if PLATFORM == 'Windows':
		_open_local_files_win(paths, pane)
	elif PLATFORM == 'Mac':
		_open_local_files_mac(paths)
	else:
		assert PLATFORM == 'Linux'
		_open_local_files_linux(paths)

def _open_local_files_win(paths, pane):
	# Whichever implementation is used here, it should support:
	#  * C:\picture.jpg
	#  * C:\notepad.exe
	#  * C:\a & b.txt
	#  * C:\batch.bat should print the current dir:
	#        echo %cd%
	#        pause
	#  * \\server\share\picture.jpg
	#  * D:\Book.pdf
	#  * \\cryptomator-vault\app.exe
	for path in paths:
		if is_shortcut(path):
			target = shortcut_target(path)
			if target and is_dir(as_url(target)):
				pane.set_path(as_url(target))
				return
		from win32api import ShellExecute
		from win32con import SW_SHOWNORMAL
		import pywintypes
		from winerror import ERROR_CANCELLED
		try:
			cwd = os.path.dirname(path)
			ShellExecute(0, None, path, None, cwd, SW_SHOWNORMAL)
		except pywintypes.error as e:
			# This for instance happens when the file is an .exe that requires
			# Admin privileges, but the user cancels the UAC "do you want to run
			# this file?" dialog.
			if e.winerror != ERROR_CANCELLED:
				_offer_open_with_win(path, cwd, e.strerror)

def _offer_open_with_win(path, cwd, reason):
	# A broken association can be reset in the Windows "Open with" dialog.
	from win32api import ShellExecute
	from win32con import SW_SHOWNORMAL
	import pywintypes
	message = 'Could not open %s:\n%s\n\nChoose the app Windows uses for this file?' % (
		path, reason
	)
	if show_alert(message, YES | NO, YES) & YES:
		try:
			ShellExecute(0, 'openas', path, None, cwd, SW_SHOWNORMAL)
		except pywintypes.error as e:
			show_alert(
				'Could not show the "Open with" dialog for %s:\n%s' % (
					path, e.strerror
				)
			)

class OpenSelectedFiles(DirectoryPaneCommand):
	def __call__(self):
		file_under_cursor = self.pane.get_file_under_cursor()
		selected_files = self.pane.get_selected_files()
		if file_under_cursor in selected_files:
			_open_files(selected_files, self.pane)
		else:
			_open_files([file_under_cursor], self.pane)
	def is_visible(self):
		return bool(self.get_chosen_files())

def _is_viewable(url):
	# Whether any registered viewer handles url's content - the built-in
	# image/video/text ones (core/viewers.py) plus whatever plugins added.
	return viewer_for(url) is not None

def _view_file_in(source_pane, target_pane, focus_view=True):
	# Read the file under source_pane's cursor and mount the matching viewer
	# into target_pane. focus_view is forwarded to the viewer so it can be
	# mounted without grabbing keyboard focus (see ViewFileInOtherPane).
	url = source_pane.get_file_under_cursor()
	if not url:
		show_alert(NO_SELECTION)
		return
	url_is_dir = is_dir_checked(url)
	if url_is_dir is None:
		return
	if url_is_dir:
		show_alert('Cannot view a directory.')
		return
	if splitscheme(url)[0] != 'file://':
		show_alert('Can only view local files.')
		return
	viewer = viewer_for(url)
	if viewer is None:
		show_alert(
			"Can't view this file here — it looks binary. Press Enter "
			'or use Open to launch it with the default app.'
		)
		return
	viewer.show(target_pane, url, focus_view=focus_view)

class ViewFile(DirectoryPaneCommand):

	# Palette-only by design, like ResetPaneFontSize — no default key
	# binding, so it doesn't change Enter/double-click behaviour.
	aliases = ('View file',)

	def __call__(self):
		_view_file_in(self.pane, self.pane)

class ViewFileInOtherPane(DirectoryPaneCommand):

	# Like ViewFile, but mounts the viewer in the *other* pane so this pane's
	# file list stays visible. Keyboard focus deliberately stays here, so you
	# can keep browsing files while each one previews in the other pane. With
	# only one pane open, target is this pane, so the viewer takes focus as
	# usual. Palette-only by default (no key binding).
	aliases = ('View file in other pane',)

	def __call__(self):
		target = get_opposite_pane(self.pane)
		_view_file_in(self.pane, target, focus_view=target is self.pane)

class OpenOrView(DirectoryPaneCommand):

	# Folder -> navigate in (like Open); viewable file -> internal viewer
	# (like ViewFile); anything the viewer can't handle (binary, non-local)
	# -> OS-open, same as before the viewer existed. Bind to Enter to make
	# the viewer the default file action without losing folder navigation or
	# garbling binaries.
	aliases = ('Open or view',)

	def __call__(self):
		url = self.pane.get_file_under_cursor()
		url_is_dir = is_dir_checked(url) if url else False
		if url_is_dir is None:
			# Already alerted; `open` would only alert a second time.
			return
		if (url and not url_is_dir and splitscheme(url)[0] == 'file://'
				and _is_viewable(url)):
			self.pane.run_command('view_file')
		else:
			self.pane.run_command('open')
