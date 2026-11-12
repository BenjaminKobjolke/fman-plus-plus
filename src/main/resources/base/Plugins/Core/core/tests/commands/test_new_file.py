from core.commands import editor as editor_module
from core.commands.new_file import NewEmptyFile, _find_extension_start
from core.commands.editor import CreateAndEditFile
from fman import DirectoryPane
from unittest import TestCase
from unittest.mock import MagicMock, patch


class FindExtensionStartTest(TestCase):
	def test_no_extension(self):
		self.assertIsNone(_find_extension_start('File'))

	def test_normal_extension(self):
		self.assertEqual(4, _find_extension_start('test.zip'))

	def test_tar_xz(self):
		self.assertEqual(7, _find_extension_start('archive.tar.xz'))

	def test_tar_gz(self):
		self.assertEqual(7, _find_extension_start('archive.tar.gz'))


class NewEmptyFileTest(TestCase):
	def setUp(self):
		self.pane = MagicMock(spec=DirectoryPane)
		self.pane.get_path.return_value = 'file://C:/dir'
		self.pane.get_file_under_cursor.return_value = None

	def test_creates_file_and_places_cursor_without_opening_editor(self):
		with patch('core.commands.new_file.show_input', return_value='report.txt'), \
				patch('core.commands.new_file.exists', return_value=False), \
				patch('core.commands.new_file.touch') as touch:
			NewEmptyFile(self.pane)()

		touch.assert_called_once_with('file://C:/dir/report.txt')
		self.pane.place_cursor_at.assert_called_once_with(
			'file://C:/dir/report.txt'
		)

	def test_existing_file_is_not_touched(self):
		with patch('core.commands.new_file.show_input', return_value='report.txt'), \
				patch('core.commands.new_file.exists', return_value=True), \
				patch('core.commands.new_file.touch') as touch:
			NewEmptyFile(self.pane)()

		touch.assert_not_called()
		self.pane.place_cursor_at.assert_not_called()

	def test_prompt_cancellation_does_nothing(self):
		with patch('core.commands.new_file.show_input', return_value=None), \
				patch('core.commands.new_file.touch') as touch:
			NewEmptyFile(self.pane)()

		touch.assert_not_called()
		self.pane.place_cursor_at.assert_not_called()

	def test_unsupported_filesystem_shows_alert(self):
		with patch('core.commands.new_file.show_input', return_value='report.txt'), \
				patch('core.commands.new_file.exists', return_value=False), \
				patch('core.commands.new_file.touch',
					  side_effect=NotImplementedError), \
				patch('core.commands.new_file.show_alert') as show_alert:
			NewEmptyFile(self.pane)()

		show_alert.assert_called_once_with(
			'Creating an empty file is not supported here.'
		)
		self.pane.place_cursor_at.assert_not_called()

	def test_oserror_shows_path_and_reason(self):
		with patch('core.commands.new_file.show_input', return_value='report.txt'), \
				patch('core.commands.new_file.exists', return_value=False), \
				patch('core.commands.new_file.touch',
					  side_effect=OSError('disk full')), \
				patch('core.commands.new_file.as_human_readable',
					  return_value='C:/dir/report.txt'), \
				patch('core.commands.new_file.show_alert') as show_alert:
			NewEmptyFile(self.pane)()

		show_alert.assert_called_once_with(
			'Could not create C:/dir/report.txt: disk full'
		)
		self.pane.place_cursor_at.assert_not_called()

	def test_hidden_file_cursor_failure_is_ignored(self):
		with patch('core.commands.new_file.show_input', return_value='.bashrc'), \
				patch('core.commands.new_file.exists', return_value=False), \
				patch('core.commands.new_file.touch'), \
				patch.object(self.pane, 'place_cursor_at', side_effect=ValueError):
			NewEmptyFile(self.pane)()

	def test_visibility_requires_touch_support(self):
		command = NewEmptyFile(self.pane)
		with patch('core.commands.new_file._fs_implements', return_value=False) as impl:
			self.assertFalse(command.is_visible())
		impl.assert_called_once_with('file://', 'touch')
		with patch('core.commands.new_file._fs_implements', return_value=True):
			self.assertTrue(command.is_visible())

	def test_default_name_comes_from_file_under_cursor_and_selects_extension(self):
		self.pane.get_file_under_cursor.return_value = (
			'file://C:/dir/report.tar.gz'
		)
		with patch('core.commands.new_file.is_dir', return_value=False), \
				patch('core.commands.new_file.show_input', return_value=None) as prompt:
			NewEmptyFile(self.pane)()

		prompt.assert_called_once_with(
			'Enter file name to create:', 'report.tar.gz', selection_end=6
		)


class CreateAndEditFileTest(TestCase):
	def setUp(self):
		self.pane = MagicMock(spec=DirectoryPane)
		self.pane.get_path.return_value = 'file://C:/dir'
		self.pane.get_file_under_cursor.return_value = None

	def test_creates_missing_file_and_opens_it_in_editor(self):
		command = CreateAndEditFile(self.pane)
		with patch('core.commands.new_file.show_input', return_value='report.txt'), \
				patch('core.commands.new_file.exists', return_value=False), \
				patch('core.commands.new_file.touch') as touch, \
				patch.object(editor_module.OpenWithEditor, '__call__') as open_file:
			command()

		touch.assert_called_once_with('file://C:/dir/report.txt')
		self.pane.place_cursor_at.assert_called_once_with(
			'file://C:/dir/report.txt'
		)
		open_file.assert_called_once_with('file://C:/dir/report.txt')

	def test_existing_file_is_opened_without_touching(self):
		command = CreateAndEditFile(self.pane)
		with patch('core.commands.new_file.show_input', return_value='report.txt'), \
				patch('core.commands.new_file.exists', return_value=True), \
				patch('core.commands.new_file.touch') as touch, \
				patch.object(editor_module.OpenWithEditor, '__call__') as open_file:
			command()

		touch.assert_not_called()
		open_file.assert_called_once()

	def test_unsupported_filesystem_shows_editor_specific_alert(self):
		with patch('core.commands.new_file.show_input', return_value='report.txt'), \
				patch('core.commands.new_file.exists', return_value=False), \
				patch('core.commands.new_file.touch',
					  side_effect=NotImplementedError), \
				patch('core.commands.new_file.show_alert') as show_alert, \
				patch.object(editor_module.OpenWithEditor, '__call__') as open_file:
			CreateAndEditFile(self.pane)()

		show_alert.assert_called_once_with(
			'Sorry, creating a file for editing is not supported here.'
		)
		open_file.assert_not_called()
