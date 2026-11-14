"""
Reads and writes the user's own key binding file - the one the in-palette
binding editor (core/binding_editor.py) edits.

Deliberately not fman's save_json: 'Key Bindings.json' is a JSON *list*, and
save_json writes it differentially (fman/impl/plugins/config.py), which can only
append to the front of the user's file - everything after it must still match
the shipped files verbatim. Removing a binding is impossible that way. Writing
the user file directly handles add, change and remove with one mechanism, and is
the same code for the viewer bindings, which have no shipped file at all.

Reading stays on fman.load_json, so what the editor shows is the merged,
effective view (shipped + platform + user) fman itself dispatches from.
"""
import json
import os
from os.path import dirname, join, splitext

from core.key_bindings import builtin_key_active, get_shortcuts_for_command
from fman import DATA_DIRECTORY, PLATFORM, load_json, load_plugin, unload_plugin

_SETTINGS_PLUGIN = join(DATA_DIRECTORY, 'Plugins', 'User', 'Settings')

def user_bindings_path(bindings_file):
	"""
	Where the user's own copy of `bindings_file` lives, e.g.
	.../Plugins/User/Settings/Key Bindings (Windows).json.
	"""
	# Mirrors Config.locate's platform-specific name (see that module): its
	# last candidate is what save_json writes to. Duplicated rather than
	# reached for, since Config is reachable only through the running plugin
	# support's private state.
	base, ext = splitext(bindings_file)
	return join(_SETTINGS_PLUGIN, '%s (%s)%s' % (base, PLATFORM, ext))

def load_user_bindings(bindings_file):
	"""
	The user's own bindings as a list. Empty if the file is absent or the user
	hand-edited it into something that isn't a JSON list.
	"""
	path = user_bindings_path(bindings_file)
	try:
		with open(path, encoding='utf-8') as f:
			bindings = json.load(f)
	except (OSError, ValueError):
		return []
	return bindings if isinstance(bindings, list) else []

def save_user_bindings(bindings_file, bindings):
	"""
	Write `bindings` to the user's file and make them take effect immediately.
	"""
	path = user_bindings_path(bindings_file)
	os.makedirs(dirname(path), exist_ok=True)
	tmp_path = path + '.tmp'
	with open(tmp_path, 'w', encoding='utf-8') as f:
		json.dump(bindings, f, indent=4)
	os.replace(tmp_path, path)
	_reload_settings_plugin()

def _reload_settings_plugin():
	# Both files need this: the global one is only read while a plugin loads,
	# and although the viewers re-read theirs per keystroke, load_json answers
	# from Config's cache until a plugin dir is added or removed. Same cycle as
	# fman's own nonexistent_shortcut_handler.
	try:
		unload_plugin(_SETTINGS_PLUGIN)
	except ValueError:
		# Never loaded - the Settings folder did not exist until just now.
		pass
	load_plugin(_SETTINGS_PLUGIN)

def shortcuts_for(bindings_file, command_name, builtin_key=''):
	"""
	The shortcuts that currently run `command_name`, as (shortcut, is_user)
	pairs in priority order. is_user says whether the shortcut comes from the
	user's own file, which is what decides whether it can simply be removed.
	"""
	user_shortcuts = set(get_shortcuts_for_command(
		load_user_bindings(bindings_file), command_name
	))
	merged_bindings = load_json(bindings_file, default=[])
	shortcuts = [
		(shortcut, shortcut in user_shortcuts)
		for shortcut in get_shortcuts_for_command(
			merged_bindings, command_name
		)
	]
	if (
		builtin_key not in (shortcut for shortcut, _is_user in shortcuts)
		and builtin_key_active(merged_bindings, command_name, builtin_key)
	):
		shortcuts.append((builtin_key, False))
	return shortcuts
