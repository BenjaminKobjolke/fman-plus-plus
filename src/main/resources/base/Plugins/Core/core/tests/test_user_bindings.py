import json
from core.user_bindings import (
	load_user_bindings, save_user_bindings, shortcuts_for, user_bindings_path,
)
from os import makedirs
from os.path import dirname
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

_FILE = 'Key Bindings.json'

class UserBindingsPathTest(TestCase):

	def test_is_the_platform_specific_file_in_the_settings_plugin(self):
		# The same path Config.locate picks as save_json's destination.
		path = user_bindings_path(_FILE)
		self.assertTrue(path.endswith('.json'), path)
		self.assertIn('Settings', path)
		self.assertIn(' (', path)

class _TempSettings:

	"""
	Points the module at a throwaway Settings folder and swallows the plugin
	reload, which needs a running fman.
	"""

	def __init__(self, dir_):
		self._dir = dir_
	def __enter__(self):
		self._patches = [
			patch('core.user_bindings._SETTINGS_PLUGIN', self._dir),
			patch('core.user_bindings._reload_settings_plugin'),
		]
		for p in self._patches:
			p.start()
		return self
	def __exit__(self, *_):
		for p in self._patches:
			p.stop()

class LoadAndSaveTest(TestCase):

	def test_round_trip(self):
		bindings = [{'keys': ['Ctrl+Alt+P'], 'command': 'pack'}]
		with TemporaryDirectory() as tmp, _TempSettings(tmp):
			save_user_bindings(_FILE, bindings)
			self.assertEqual(bindings, load_user_bindings(_FILE))
	def test_a_missing_file_reads_as_empty(self):
		with TemporaryDirectory() as tmp, _TempSettings(tmp):
			self.assertEqual([], load_user_bindings(_FILE))
	def test_saving_creates_the_settings_folder(self):
		with TemporaryDirectory() as tmp:
			settings = tmp + '/Plugins/User/Settings'
			with _TempSettings(settings):
				save_user_bindings(_FILE, [])
				self.assertEqual([], load_user_bindings(_FILE))
	def test_the_reload_happens_so_the_binding_takes_effect(self):
		with TemporaryDirectory() as tmp, patch(
			'core.user_bindings._SETTINGS_PLUGIN', tmp
		), patch('core.user_bindings._reload_settings_plugin') as reload_:
			save_user_bindings(_FILE, [])
			reload_.assert_called_once_with()
	def test_no_temp_file_is_left_behind(self):
		# The write is atomic: a tmp file plus os.replace.
		with TemporaryDirectory() as tmp, _TempSettings(tmp):
			save_user_bindings(_FILE, [])
			path = user_bindings_path(_FILE)
			self.assertEqual([], load_user_bindings(_FILE))
			with open(path, encoding='utf-8') as f:
				self.assertEqual([], json.load(f))

class MalformedFileTest(TestCase):

	def _write(self, dir_, content):
		path = user_bindings_path(_FILE)
		makedirs(dirname(path), exist_ok=True)
		with open(path, 'w', encoding='utf-8') as f:
			f.write(content)

	def test_broken_json_reads_as_empty(self):
		with TemporaryDirectory() as tmp, _TempSettings(tmp):
			self._write(tmp, '{ not json')
			self.assertEqual([], load_user_bindings(_FILE))
	def test_a_json_object_reads_as_empty(self):
		# The file has to be a list; anything else is the user's typo.
		with TemporaryDirectory() as tmp, _TempSettings(tmp):
			self._write(tmp, '{"keys": ["M"]}')
			self.assertEqual([], load_user_bindings(_FILE))

class ShortcutsForTest(TestCase):

	def _shortcuts(self, merged, user):
		with patch(
			'core.user_bindings.load_json', return_value=merged
		), patch(
			'core.user_bindings.load_user_bindings', return_value=user
		):
			return shortcuts_for(_FILE, 'video_mute')

	def test_marks_which_shortcuts_are_the_users_own(self):
		user = [{'keys': ['M'], 'command': 'video_mute'}]
		shipped = [{'keys': ['Ctrl+M'], 'command': 'video_mute'}]
		self.assertEqual(
			[('M', True), ('Ctrl+M', False)], self._shortcuts(user + shipped, user)
		)
	def test_other_commands_are_left_out(self):
		merged = [{'keys': ['F5'], 'command': 'copy'}]
		self.assertEqual([], self._shortcuts(merged, []))
	def test_a_shortcut_stolen_by_a_higher_priority_binding_is_hidden(self):
		# get_shortcuts_for_command already hides it, so the list never
		# advertises a key that would run something else.
		merged = [
			{'keys': ['M'], 'command': 'pack'},
			{'keys': ['M'], 'command': 'video_mute'},
		]
		self.assertEqual([], self._shortcuts(merged, []))

	def test_appends_an_active_builtin_key_as_default(self):
		with patch(
			'core.user_bindings.load_json', return_value=[]
		), patch(
			'core.user_bindings.load_user_bindings', return_value=[]
		):
			self.assertEqual(
				[('/', False)], shortcuts_for(_FILE, 'text_find', builtin_key='/')
			)

	def test_lists_a_user_bound_builtin_key_only_once(self):
		bindings = [{'keys': ['/'], 'command': 'text_find'}]
		with patch(
			'core.user_bindings.load_json', return_value=bindings
		), patch(
			'core.user_bindings.load_user_bindings', return_value=bindings
		):
			self.assertEqual(
				[('/', True)], shortcuts_for(_FILE, 'text_find', builtin_key='/')
			)

	def test_hides_a_builtin_key_shadowed_with_do_nothing(self):
		bindings = [{'keys': ['/'], 'command': 'do_nothing'}]
		with patch(
			'core.user_bindings.load_json', return_value=bindings
		), patch(
			'core.user_bindings.load_user_bindings', return_value=bindings
		):
			self.assertEqual(
				[], shortcuts_for(_FILE, 'text_find', builtin_key='/')
			)
