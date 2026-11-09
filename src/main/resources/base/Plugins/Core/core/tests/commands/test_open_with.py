from core.commands.open_with import EditApp, _add_app, _open_files_with_app
from unittest import TestCase
from unittest.mock import patch


class OpenWithArgumentsTest(TestCase):
	def setUp(self):
		self.apps = {}
		self.patches = [
			patch('core.commands.open_with._load_apps', return_value=self.apps),
			patch('core.commands.open_with._save_apps'),
			patch('core.commands.open_with._load_file_associations', return_value={}),
			patch('core.commands.open_with._save_file_associations'),
		]
		for patcher in self.patches:
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_add_app_saves_parameterized_value(self):
		with patch(
			'core.commands.open_with._show_app_open_dialog',
			return_value='C:/Program Files/VideoLAN/vlc.exe'
		), patch('core.commands.open_with.show_input', return_value='VLC'), patch(
			'core.commands.open_with.ask_arguments',
			return_value=['--fullscreen', '{file}']
		):
			self.assertEqual('VLC', _add_app())
		self.assertEqual(
			{'VLC': '"C:/Program Files/VideoLAN/vlc.exe" --fullscreen {file}'},
			self.apps,
		)

	def test_add_app_saves_plain_path_when_arguments_are_default(self):
		with patch(
			'core.commands.open_with._show_app_open_dialog',
			return_value='C:/Program Files/VLC/vlc.exe'
		), patch('core.commands.open_with.show_input', return_value='VLC'), patch(
			'core.commands.open_with.ask_arguments', return_value=['{file}']
		):
			_add_app()
		self.assertEqual({'VLC': 'C:/Program Files/VLC/vlc.exe'}, self.apps)

	def test_cancelled_arguments_do_not_save_app(self):
		with patch(
			'core.commands.open_with._show_app_open_dialog', return_value='vlc'
		), patch('core.commands.open_with.show_input', return_value='VLC'), patch(
			'core.commands.open_with.ask_arguments', return_value=None
		):
			self.assertIsNone(_add_app())
		self.assertEqual({}, self.apps)

	def test_edit_parses_existing_command_and_saves_new_arguments(self):
		self.apps['VLC'] = 'flatpak run org.videolan.VLC {file}'
		with patch(
			'core.commands.open_with.show_input', return_value='Video Player'
		), patch(
			'core.commands.open_with.show_file_open_dialog', return_value='flatpak'
		) as dialog, patch(
			'core.commands.open_with.ask_arguments',
			return_value=['--new', '{file}']
		) as ask, patch('core.commands.open_with.rename_app') as rename, patch(
			'core.commands.open_with._remap_app_associations'
		), patch('core.commands.open_with.show_alert'):
			EditApp([]).on_selected('VLC')
		dialog.assert_called_once()
		self.assertEqual('flatpak', dialog.call_args.args[1])
		ask.assert_called_once_with('run org.videolan.VLC {file}')
		self.assertEqual(
			{'Video Player': 'flatpak --new {file}'}, self.apps
		)
		rename.assert_called_once_with(
			'VLC', 'Video Player', 'flatpak --new {file}'
		)

	def test_edit_plain_app_prompts_with_file_placeholder(self):
		self.apps['VLC'] = 'C:/Program Files/VLC/vlc.exe'
		with patch(
			'core.commands.open_with.show_input', return_value='VLC'
		), patch(
			'core.commands.open_with.show_file_open_dialog', return_value='vlc'
		), patch(
			'core.commands.open_with.ask_arguments', return_value=['{file}']
		) as ask, patch('core.commands.open_with._remap_app_associations'), patch(
			'core.commands.open_with.rename_app'
		), patch('core.commands.open_with.show_alert'), patch(
			'core.file_type_actions.exists', return_value=True
		):
			EditApp([]).on_selected('VLC')
		ask.assert_called_once_with('{file}')

	def test_open_plain_app_passes_all_files_in_one_call(self):
		self.apps['VLC'] = 'C:/Program Files/VLC/vlc.exe'
		with patch('core.file_type_actions.exists', return_value=True), patch(
			'core.commands.open_with.Popen'
		) as popen:
			_open_files_with_app(['a', 'b'], 'VLC')
		popen.assert_called_once_with(['C:/Program Files/VLC/vlc.exe', 'a', 'b'])

	def test_open_embedded_placeholder_launches_once_per_file(self):
		self.apps['VLC'] = 'vlc --file={file}'
		with patch('core.commands.open_with.Popen') as popen:
			_open_files_with_app(['a', 'b'], 'VLC')
		self.assertEqual(
			[(["vlc", "--file=a"],), (["vlc", "--file=b"],)],
			[call.args for call in popen.call_args_list],
		)

	def test_non_string_app_value_shows_configuration_alert(self):
		self.apps['VLC'] = ['vlc', '{file}']
		with patch('core.commands.open_with.show_alert') as alert:
			_open_files_with_app(['a'], 'VLC')
		alert.assert_called_once_with('Could not find the configuration for VLC.')

	def test_start_error_shows_alert(self):
		self.apps['VLC'] = 'missing-app --open {file}'
		with patch(
			'core.commands.open_with.Popen', side_effect=FileNotFoundError('missing')
		), patch('core.commands.open_with.show_alert') as alert:
			_open_files_with_app(['a'], 'VLC')
		self.assertIn('Could not start VLC', alert.call_args.args[0])
