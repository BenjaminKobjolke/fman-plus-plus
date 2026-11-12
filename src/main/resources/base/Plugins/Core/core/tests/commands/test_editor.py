import os
import tempfile
from core.commands import editor as editor_module
from core.commands.editor import configure_editor
from core.text_editor import build_editor_setting, format_arguments
from fman import CANCEL, OK
from fman.url import as_url
from unittest import TestCase
from unittest.mock import patch


class ConfigureEditorTest(TestCase):
	def setUp(self):
		self.settings = {'editor': {
			'args': ['old-editor', '--old', '{file}']
		}}
		self.patches = [
			patch.object(editor_module, 'load_json', return_value=self.settings),
			patch.object(editor_module, 'save_json'),
			patch.object(editor_module, 'show_quicksearch'),
			patch.object(editor_module, 'show_file_open_dialog'),
			patch.object(editor_module, 'show_input'),
			patch.object(editor_module, 'show_alert'),
			patch.object(editor_module, 'show_status_message'),
		]
		(self.load_json, self.save_json, self.show_quicksearch,
		 self.show_file_open_dialog, self.show_input, self.show_alert,
		 self.show_status_message) = [p.start() for p in self.patches]
		self.addCleanup(self._stop_patches)

	def _stop_patches(self):
		for patcher in reversed(self.patches):
			patcher.stop()

	def _choose(self, name):
		self.show_quicksearch.return_value = ('', name)
		self.show_file_open_dialog.return_value = '/editors/ecode'

	def test_preset_saves_setting(self):
		self._choose('Ecode')
		result = configure_editor()
		self.assertEqual(
			build_editor_setting('/editors/ecode', ['--zen-mode']), result
		)
		self.assertIs(result, self.settings['editor'])
		self.save_json.assert_called_once_with('Core Settings.json')
		self.show_input.assert_not_called()
		self.show_status_message.assert_called_once_with(
			'Text editor saved.', timeout_secs=3
		)

	def test_manual_arguments_are_prefilled_and_saved(self):
		self._choose('Manual configuration')
		self.show_input.return_value = '--flag "a path"'
		with patch.object(editor_module, 'PLATFORM', 'Windows'):
			result = configure_editor()
		self.show_input.assert_called_once_with(
			'Arguments for the editor (the file is added last):',
			format_arguments(['--old'])
		)
		self.assertEqual(
			build_editor_setting('/editors/ecode', ['--flag', 'a path']), result
		)
		self.save_json.assert_called_once_with('Core Settings.json')

	def test_cancel_at_each_dialog_leaves_setting_unchanged(self):
		for cancel_at in ('list', 'file', 'prompt'):
			with self.subTest(cancel_at=cancel_at):
				self.save_json.reset_mock()
				self.show_quicksearch.reset_mock()
				self.show_file_open_dialog.reset_mock()
				self.show_input.reset_mock()
				original = self.settings['editor']
				if cancel_at == 'list':
					self.show_quicksearch.return_value = ('', None)
				elif cancel_at == 'file':
					self._choose('Ecode')
					self.show_file_open_dialog.return_value = ''
				else:
					self._choose('Manual configuration')
					self.show_input.return_value = None
				self.assertEqual({}, configure_editor())
				self.save_json.assert_not_called()
				self.assertIs(original, self.settings['editor'])

	def test_file_dialog_starts_in_existing_executable_folder(self):
		with tempfile.TemporaryDirectory() as directory:
			executable = os.path.join(directory, 'editor.exe')
			with open(executable, 'w'):
				pass
			self.settings['editor'] = {'args': [executable, '{file}']}
			self._choose('Ecode')
			configure_editor()
		self.show_file_open_dialog.assert_called_once_with(
			'Pick an Editor', directory, editor_module._PLATFORM_APPLICATIONS_FILTER[
				editor_module.PLATFORM
			]
		)

	def test_file_dialog_uses_applications_directory_for_missing_executable(self):
		self._choose('Ecode')
		with patch.object(editor_module, '_get_applications_directory',
			return_value='/applications'):
			configure_editor()
		self.show_file_open_dialog.assert_called_once_with(
			'Pick an Editor', '/applications',
			editor_module._PLATFORM_APPLICATIONS_FILTER[
				editor_module.PLATFORM
			]
		)

	def test_unknown_choice_does_not_open_dialog(self):
		self.show_quicksearch.return_value = ('', 'unknown')
		self.assertEqual({}, configure_editor())
		self.show_file_open_dialog.assert_not_called()
		self.save_json.assert_not_called()

	def test_invalid_manual_arguments_show_alert(self):
		self._choose('Manual configuration')
		self.show_input.return_value = '"unclosed'
		with patch.object(editor_module, 'PLATFORM', 'Linux'):
			with patch('core.text_editor.PLATFORM', 'Linux'):
				self.assertEqual({}, configure_editor())
		self.show_alert.assert_called_once()
		self.save_json.assert_not_called()


class OpenWithEditorConfigurationTest(TestCase):
	def test_missing_editor_can_open_wizard_or_cancel(self):
		settings = {}
		with patch.object(editor_module, 'load_json', return_value=settings), \
			patch.object(editor_module, 'show_alert', return_value=OK), \
			patch.object(
				editor_module, 'configure_editor', return_value={'args': []}
			) as wizard:
			self.assertEqual(
				{'args': []}, editor_module.OpenWithEditor(None)._get_editor()
			)
			wizard.assert_called_once_with()
		with patch.object(editor_module, 'load_json', return_value=settings), \
			patch.object(editor_module, 'show_alert', return_value=CANCEL), \
			patch.object(editor_module, 'configure_editor') as wizard:
			self.assertEqual({}, editor_module.OpenWithEditor(None)._get_editor())
			wizard.assert_not_called()


class OpenWithEditorUncTest(TestCase):
	def test_unc_path_is_passed_to_editor_as_a_windows_path(self):
		url = as_url(r'\\localhost\c$\Windows\win.ini')
		with patch.object(editor_module, 'resolve', return_value=url), \
				patch.object(editor_module, 'load_json', return_value={
					'editor': {'args': ['editor.exe', '{file}']}
				}), \
				patch.object(editor_module.os.path, 'exists', return_value=True), \
				patch.object(editor_module, 'Popen') as popen:
			editor_module.OpenWithEditor(None)(url=url)

		kwargs = popen.call_args.kwargs
		self.assertEqual(r'\\localhost\c$\Windows\win.ini', kwargs['args'][-1])
		self.assertNotIn('cwd', kwargs)
