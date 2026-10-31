""""Open with...": the user's own list of applications.

'Apps.json' stores the applications the user picked; 'File Associations.json'
counts how often each was used per filename suffix, which is what orders the
list - most-used app for this suffix first, then everything else.
"""
# `import *` skips underscore names, and OpenWith's app dialogs are the editor
# picker with a different caption.
from core.commands.editor import _PLATFORM_APPLICATIONS_FILTER, \
	_show_app_open_dialog
from core.commands.util import is_file_url, NO_SELECTION
from core.commands.file_types import ChooseFileTypeAction
from core.file_type_actions import (
	action_for_exact_suffix, remove_action, rename_app, suffix_of,
)
from core.os_ import get_popen_kwargs_for_opening
from core.quicksearch_screen import QuicksearchScreen
from fman import DirectoryPaneCommand, PLATFORM, load_json, save_json, \
	show_alert, show_file_open_dialog, show_prompt, show_status_message
from fman.fs import resolve
from fman.url import as_human_readable, splitscheme
from subprocess import Popen

import os
import os.path

__all__ = [
	'Configure', 'EditApp', 'OpenWith', 'RemoveApp', 'ShowAppsForOpening'
]

class OpenWith(DirectoryPaneCommand):

	aliases = 'Open with...',
	usable_in_viewer = True

	_OTHER = 'Other...'

	def __call__(self, app=None):
		files, error_msg = self._get_chosen_files()
		if error_msg:
			show_alert(error_msg)
			return
		is_first_execution = not _load_apps()
		if is_first_execution:
			app = _add_app()
			if app:
				_open_files_with_app(files, app)
		else:
			if app is None:
				ShowAppsForOpening(files).show()
			else:
				_open_files_with_app(files, app)
	def _get_chosen_files(self):
		urls = self.get_chosen_files()
		if not urls:
			return [], NO_SELECTION
		files = []
		for url in urls:
			try:
				url_resolved = resolve(url)
			except OSError:
				pass
			else:
				scheme, path = splitscheme(url_resolved)
				if scheme != 'file://':
					return \
						[], 'Sorry, opening %s files is not supported.' % scheme
				files.append(as_human_readable(url_resolved))
		return files, ''
	def is_visible(self):
		pane = self.pane
		return is_file_url(pane.get_path()) and pane.get_file_under_cursor()

def _open_files_with_app(files, app):
	associations = _load_file_associations()
	for file_path in files:
		file_name = os.path.basename(file_path)
		extension = suffix_of(file_name)
		ext_assocs = associations.setdefault(extension, {})
		ext_assocs[app] = ext_assocs.get(app, 0) + 1
	_save_file_associations()
	apps = _load_apps()
	try:
		app_path = apps[app]
	except KeyError:
		# We don't expect this to happen. But JSON files are always susceptible
		# by becoming corrupted, eg. when the user edits them.
		show_alert('Could not find the configuration for %s.' % app)
		return
	Popen(**get_popen_kwargs_for_opening(files, with_=app_path))

def _load_file_associations():
	return load_json('File Associations.json', {})

def _save_file_associations():
	save_json('File Associations.json')

def _load_apps():
	return load_json('Apps.json', {})

def _save_apps():
	save_json('Apps.json')

def _add_app():
	app_path = _show_app_open_dialog('Pick an application')
	if not app_path:
		return
	app_name = os.path.basename(app_path).split('.')[0].capitalize()
	app_name, ok = show_prompt(
		'Please enter a name for the application:', app_name
	)
	if not ok or not app_name:
		return
	apps = _load_apps()
	apps[app_name] = app_path
	_save_apps()
	return app_name

def _remove_app(app):
	apps = _load_apps()
	# pop, not del: JSON files are always susceptible by becoming corrupted,
	# eg. when the user edits them.
	apps.pop(app, None)
	_save_apps()
	_remap_app_associations(app)

def _remap_app_associations(app, new_name=None):
	# One pass over 'File Associations.json'. `new_name=None` drops the app
	# from every suffix, and the suffix itself once no app is left for it;
	# otherwise its usage counts move to the new name, so a renamed app keeps
	# its place in the "Open with..." order.
	associations = _load_file_associations()
	for suffix, apps_for_suffix in list(associations.items()):
		count = apps_for_suffix.pop(app, None)
		if new_name is not None:
			if count is not None:
				apps_for_suffix[new_name] = count
		elif not apps_for_suffix:
			del associations[suffix]
	_save_file_associations()

class ShowAppsForOpening(QuicksearchScreen):

	_CONFIGURE = 'Configure...'

	def __init__(self, files):
		super().__init__()
		self._files = files
	def get_options(self):
		file_associations = sorted(
			_load_file_associations().items(),
			key=lambda tpl: -len(tpl[0])
		)
		already_yielded = set()
		for file_path in self._files:
			fname = os.path.basename(file_path)
			for suffix, associations in file_associations:
				if fname.endswith(suffix) and (suffix or '.' not in fname):
					for app, count in sorted(
						associations.items(), key=lambda tpl: tpl[1],
						reverse=True
					):
						if app not in already_yielded:
							yield app
							already_yielded.add(app)
		for app in sorted(_load_apps()):
			if app not in already_yielded:
				yield app
		yield self._CONFIGURE
	def on_selected(self, option):
		if option == self._CONFIGURE:
			Configure(self._files).show()
		else:
			_open_files_with_app(self._files, option)

class Configure(QuicksearchScreen):

	_ADD_APP = 'Add app...'
	_EDIT_APP = 'Edit app...'
	_REMOVE_APP = 'Remove app...'

	def __init__(self, files):
		super().__init__()
		self._files = files
	def get_options(self):
		yield self._ADD_APP
		yield self._EDIT_APP
		yield self._REMOVE_APP
		yield from self._file_type_action_handlers()
	def on_selected(self, option):
		if option == self._ADD_APP:
			app = _add_app()
			if app:
				_open_files_with_app(self._files, app)
		elif option == self._EDIT_APP:
			EditApp(self._files).show()
		elif option == self._REMOVE_APP:
			RemoveApp(self._files).show()
		else:
			handler = self._file_type_action_handlers().get(option)
			if handler:
				handler()
	def _file_type_action_handlers(self):
		suffixes = sorted({
			suffix_of(os.path.basename(file_path)).lower()
			for file_path in self._files
			if suffix_of(os.path.basename(file_path))
		})
		handlers = {}
		for suffix in suffixes:
			handlers['Always open %s files with...' % suffix] = \
				lambda suffix=suffix: ChooseFileTypeAction(
					suffix, _load_apps(),
					lambda: Configure(self._files).show()
				).show()
			action = action_for_exact_suffix(suffix)
			if action:
				label = 'Stop always opening %s files with %s' % (
					suffix, action.label()
				)
				handlers[label] = lambda suffix=suffix, label=label: \
					_remove_file_type_action(suffix, label)
		return handlers
	def on_cancelled(self):
		ShowAppsForOpening(self._files).show()

class EditApp(QuicksearchScreen):
	def __init__(self, files):
		super().__init__()
		self._files = files
	def get_options(self):
		yield from sorted(_load_apps())
	def on_selected(self, app):
		new_name, ok = \
			show_prompt('Enter the new name for the application:', app)
		if not ok or not new_name:
			Configure(self._files).show()
			return
		apps = _load_apps()
		app_path = apps[app]
		new_path = show_file_open_dialog(
			"Pick an executable", app_path,
			_PLATFORM_APPLICATIONS_FILTER[PLATFORM]
		)
		if not new_path:
			Configure(self._files).show()
			return
		del apps[app]
		apps[new_name] = new_path
		_save_apps()
		_remap_app_associations(app, new_name)
		rename_app(app, new_name, new_path)
		show_alert('%s was updated.' % new_name)
	def on_cancelled(self):
		Configure(self._files).show()

class RemoveApp(QuicksearchScreen):
	def __init__(self, files):
		super().__init__()
		self._files = files
	def get_options(self):
		yield from sorted(_load_apps())
	def on_selected(self, app):
		_remove_app(app)
		show_alert('%s was removed from your favorite apps.' % app)
	def on_cancelled(self):
		Configure(self._files).show()

def _remove_file_type_action(suffix, label):
	remove_action(suffix)
	show_status_message(
		'%s was removed; Enter now uses the system default.' % label,
		timeout_secs=3
	)
