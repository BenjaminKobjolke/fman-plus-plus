"""Editing files: the configured external editor and its setup command.

`CreateAndEditFile` subclasses `OpenWithEditor` so a newly created file is
handed straight to the same editor, with the same "pick one" flow when none is
configured yet. `SetTextEditor` configures that external editor.
"""
from core.commands.util import create_as_admin, get_program_files, \
	get_program_files_x86, require_file_url, NO_SELECTION
from core.text_editor import (
	MANUAL, PRESETS, build_editor_setting, format_arguments, parse_arguments,
	split_editor_setting
)
from core.util import strformat_dict_values
from fman import CANCEL, DirectoryPaneCommand, load_json, OK, PLATFORM, \
	QuicksearchItem, save_json, show_alert, show_file_open_dialog, \
	show_input, show_quicksearch, show_status_message
from fman.fs import exists, is_dir, resolve, touch
from fman.url import as_human_readable, join
# os.path.basename, not fman.url's: it is applied to the name part of a URL,
# which is what core/commands/__init__.py did before this module existed.
from os.path import basename
from pathlib import PurePath
from subprocess import Popen

import os
import sys

__all__ = ['CreateAndEditFile', 'OpenWithEditor', 'SetTextEditor']

class OpenWithEditor(DirectoryPaneCommand):

	aliases = ('Edit',)
	usable_in_viewer = True

	def __call__(self, url=None):
		if url is None:
			url = self.pane.get_file_under_cursor()
		if not url:
			show_alert(NO_SELECTION)
			return
		url = resolve(url)
		if not require_file_url(url, 'Editing'):
			return
		editor = self._get_editor()
		if editor:
			file_path = as_human_readable(url)
			popen_kwargs = strformat_dict_values(editor, {'file': file_path})
			Popen(**popen_kwargs)
	def _get_editor(self):
		settings = load_json('Core Settings.json', default={})
		result = settings.get('editor', {})
		if result:
			executable_path, _ = split_editor_setting(result)
			if executable_path and os.path.exists(executable_path):
				return result
			message = 'Could not find your editor. Please select it again.'
		else:
			message = 'Editor is currently not configured. Please pick one.'
		choice = show_alert(message, OK | CANCEL, OK)
		if choice & OK:
			return configure_editor()
		return {}


def configure_editor() -> dict[str, list[str]]:
	settings = load_json('Core Settings.json', default={})
	executable, arguments = split_editor_setting(settings.get('editor'))
	options = [name for name, _ in PRESETS] + [MANUAL]
	result = show_quicksearch(
		lambda query: (
			QuicksearchItem(option) for option in options
			if query.lower() in option.lower()
		)
	)
	if not result:
		return {}
	option = result[1]
	if option not in options:
		return {}
	directory = os.path.dirname(executable) if executable and \
		os.path.exists(executable) else None
	path = _show_app_open_dialog('Pick an Editor', directory)
	if not path:
		return {}
	if option == MANUAL:
		text = show_input(
			'Arguments for the editor (the file is added last):',
			format_arguments(arguments)
		)
		if text is None:
			return {}
		try:
			arguments = parse_arguments(text)
		except (ValueError, OSError) as error:
			show_alert('Could not read the arguments: %s' % error)
			return {}
	else:
		arguments = next(args for name, args in PRESETS if name == option)
	result = build_editor_setting(path, arguments)
	settings['editor'] = result
	save_json('Core Settings.json')
	show_status_message('Text editor saved.', timeout_secs=3)
	return result


def _show_app_open_dialog(caption, directory=None):
	return show_file_open_dialog(
		caption, directory or _get_applications_directory(),
		_PLATFORM_APPLICATIONS_FILTER[PLATFORM]
	)

_PLATFORM_APPLICATIONS_FILTER = {
	'Mac': 'Applications (*.app)',
	'Windows': 'Applications (*.exe)',
	'Linux': 'Applications (*)'
}

def _get_applications_directory():
	if PLATFORM == 'Mac':
		return '/Applications'
	elif PLATFORM == 'Windows':
		result = get_program_files()
		if not os.path.exists(result):
			result = get_program_files_x86()
		if not os.path.exists(result):
			result = PurePath(sys.executable).anchor
		return result
	elif PLATFORM == 'Linux':
		return '/usr/bin'
	raise NotImplementedError(PLATFORM)


class SetTextEditor(DirectoryPaneCommand):
	aliases = ('Set text editor',)
	usable_in_viewer = True

	def __call__(self):
		configure_editor()


class CreateAndEditFile(OpenWithEditor):

	aliases = ('New file',)
	# It creates a file in the hidden list, so it must not inherit the flag.
	usable_in_viewer = False

	def __call__(self, url=None):
		file_under_cursor = self.pane.get_file_under_cursor()
		default_name = ''
		if file_under_cursor:
			try:
				file_is_dir = is_dir(file_under_cursor)
			except OSError:
				file_is_dir = False
			if not file_is_dir:
				default_name = basename(file_under_cursor)
		selection_end = _find_extension_start(default_name)
		file_name = show_input(
			'Enter file name to create/edit:', default_name,
			selection_end=selection_end
		)
		if file_name:
			file_to_edit = join(self.pane.get_path(), file_name)
			if not exists(file_to_edit):
				try:
					touch(file_to_edit)
				except PermissionError as e:
					if not create_as_admin(file_to_edit, is_dir=False, error=e):
						return
				except NotImplementedError:
					show_alert(
						'Sorry, creating a file for editing is not supported '
						'here.'
					)
					return
			try:
				self.pane.place_cursor_at(file_to_edit)
			except ValueError:
				# This can happen when the file is hidden. Eg .bashrc on Linux.
				pass
			super().__call__(file_to_edit)

def _find_extension_start(file_name, start=0):
	for dual_extension in ('.pkg.tar.xz', '.tar.xz', '.tar.gz'):
		if file_name.endswith(dual_extension):
			return len(file_name) - len(dual_extension)
	try:
		return file_name.rindex('.', start)
	except ValueError:
		return None
