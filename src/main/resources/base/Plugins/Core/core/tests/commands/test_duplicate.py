from core.commands.duplicate import DuplicateFile, suggest_duplicate_name
from core.commands.transfer import Copy
from fman.url import as_human_readable
from unittest import TestCase
from unittest.mock import Mock, patch


class SuggestDuplicateNameTest(TestCase):
	def test_uses_first_free_name_in_series(self):
		with patch('core.commands.duplicate.fman.fs.exists',
		           side_effect=lambda url: url in {
			           'file:///dir/report Copy 1.txt',
			           'file:///dir/report Copy 2.txt'}):
			name = suggest_duplicate_name('file:///dir/report.txt')
		self.assertEqual('report Copy 3.txt', name)

	def test_directory_name_has_no_extension(self):
		with (
			patch('core.commands.duplicate.fman.fs.is_dir', return_value=True),
			patch('core.commands.duplicate.fman.fs.exists', return_value=False),
		):
			name = suggest_duplicate_name('file:///dir/Archive.tar')
		self.assertEqual('Archive.tar Copy 1', name)

	def test_dotfile_keeps_its_name_as_stem(self):
		with patch('core.commands.duplicate.fman.fs.exists', return_value=False):
			name = suggest_duplicate_name('file:///dir/.env')
		self.assertEqual('.env Copy 1', name)

	def test_uses_url_paths_for_non_file_schemes(self):
		with patch(
			'core.commands.duplicate.fman.fs.exists', return_value=False
		) as exists:
			name = suggest_duplicate_name('zip:///dir/archive.zip/report.txt')
		exists.assert_called_once_with(
			'zip:///dir/archive.zip/report Copy 1.txt'
		)
		self.assertEqual('report Copy 1.txt', name)


class DuplicateFileTest(TestCase):
	def test_is_a_copy_command(self):
		self.assertTrue(issubclass(DuplicateFile, Copy))

	def test_targets_active_pane_and_uses_suggested_name_in_prompt(self):
		pane = Mock()
		pane.get_path.return_value = 'file:///active'
		pane.get_file_under_cursor.return_value = 'file:///source/report.txt'
		command = DuplicateFile(pane)
		command.get_chosen_files = Mock(
			return_value=['file:///source/report.txt']
		)
		prompt_args = []
		with (
			patch('core.commands.duplicate.suggest_duplicate_name',
			      return_value='report Copy 1.txt'),
			patch('core.commands.transfer.fman.show_input',
			      side_effect=lambda *args, **kwargs: prompt_args.append(args) or None),
			patch('core.commands.transfer.fman.fs.exists', return_value=False),
		):
			command()
		self.assertTrue(
			prompt_args[0][0].startswith('Copy "report Copy 1.txt" to\n')
		)
		self.assertTrue(prompt_args[0][0].endswith(
			as_human_readable('file:///active')
		))
		self.assertEqual('report Copy 1.txt', prompt_args[0][1])
		self.assertEqual(0, prompt_args[0][2])
		self.assertEqual(len('report Copy 1'), prompt_args[0][3])

	def test_aliases(self):
		self.assertEqual(
			('Create a duplicate file', 'Copy file here', 'Duplicate file'),
			DuplicateFile.aliases
		)

	def test_copy_verb_and_undo_recording_are_inherited(self):
		self.assertEqual('copy', DuplicateFile._verb())
		self.assertIs(DuplicateFile._record_operation, Copy._record_operation)
