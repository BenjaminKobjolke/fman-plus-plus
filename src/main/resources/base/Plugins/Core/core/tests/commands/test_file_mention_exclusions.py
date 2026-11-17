from unittest import TestCase
from unittest.mock import patch

from core.commands.file_mention_exclusions import (
	ExcludeFolderFromFileMention, IncludeFolderInFileMention,
)
from core.tests.commands import FakePane


class ExcludeFolderFromFileMentionTest(TestCase):
	def test_add_saves_existing_names_and_new_name(self):
		with (
			patch(
				'core.commands.file_mention_exclusions.get_setting',
				return_value=['.git']
			),
			patch(
				'core.commands.file_mention_exclusions.show_prompt',
				return_value='node_modules'
			),
			patch(
				'core.commands.file_mention_exclusions.save_setting'
			) as save_setting,
			patch(
				'core.commands.file_mention_exclusions.show_status_message'
			),
		):
			ExcludeFolderFromFileMention(FakePane())()

		save_setting.assert_called_once_with(
			'Core Settings.json', 'file_mention_excluded',
			['.git', 'node_modules']
		)

	def test_add_prefills_folder_under_cursor(self):
		with (
			patch(
				'core.commands.file_mention_exclusions.fman.fs.is_dir',
				return_value=True
			),
			patch(
				'core.commands.file_mention_exclusions.get_setting',
				return_value=[]
			),
			patch(
				'core.commands.file_mention_exclusions.show_prompt',
				return_value=None
			) as show_prompt,
		):
			ExcludeFolderFromFileMention(
				FakePane(url='file:///C:/Work/Projects')
			)()

		show_prompt.assert_called_once_with(
			'Folder name to skip in @ file search:', default='Projects'
		)

	def test_add_does_not_save_duplicate_ignoring_case(self):
		with (
			patch(
				'core.commands.file_mention_exclusions.get_setting',
				return_value=['Node_Modules']
			),
			patch(
				'core.commands.file_mention_exclusions.show_prompt',
				return_value='node_modules'
			),
			patch(
				'core.commands.file_mention_exclusions.save_setting'
			) as save_setting,
			patch(
				'core.commands.file_mention_exclusions.show_status_message'
			) as show_status,
		):
			ExcludeFolderFromFileMention(FakePane())()

		save_setting.assert_not_called()
		show_status.assert_called_once_with('Already excluded: node_modules')

	def test_add_does_not_save_empty_or_cancelled_prompt(self):
		for prompt_result in ('  ', None):
			with self.subTest(prompt_result=prompt_result):
				with (
					patch(
						'core.commands.file_mention_exclusions.get_setting',
						return_value=[]
					),
					patch(
						'core.commands.file_mention_exclusions.show_prompt',
						return_value=prompt_result
					),
					patch(
						'core.commands.file_mention_exclusions.save_setting'
					) as save_setting,
				):
					ExcludeFolderFromFileMention(FakePane())()

				save_setting.assert_not_called()

	def test_add_rejects_slashes(self):
		for name in ('foo/bar', 'foo\\bar'):
			with self.subTest(name=name):
				with (
					patch(
						'core.commands.file_mention_exclusions.get_setting',
						return_value=[]
					),
					patch(
						'core.commands.file_mention_exclusions.show_prompt',
						return_value=name
					),
					patch(
						'core.commands.file_mention_exclusions.save_setting'
					) as save_setting,
					patch(
						'core.commands.file_mention_exclusions.show_status_message'
					) as show_status,
				):
					ExcludeFolderFromFileMention(FakePane())()

				save_setting.assert_not_called()
				show_status.assert_called_once()


class IncludeFolderInFileMentionTest(TestCase):
	def test_remove_saves_names_without_selected_name(self):
		with (
			patch(
				'core.commands.file_mention_exclusions.get_setting',
				return_value=['.git', 'node_modules']
			),
			patch(
				'core.commands.file_mention_exclusions.show_quicksearch',
				return_value=(None, 'node_modules')
			),
			patch(
				'core.commands.file_mention_exclusions.save_setting'
			) as save_setting,
		):
			IncludeFolderInFileMention(FakePane())()

		save_setting.assert_called_once_with(
			'Core Settings.json', 'file_mention_excluded', ['.git']
		)

	def test_remove_saves_empty_list_when_last_name_is_removed(self):
		with (
			patch(
				'core.commands.file_mention_exclusions.get_setting',
				return_value=['.git']
			),
			patch(
				'core.commands.file_mention_exclusions.show_quicksearch',
				return_value=(None, '.git')
			),
			patch(
				'core.commands.file_mention_exclusions.save_setting'
			) as save_setting,
		):
			IncludeFolderInFileMention(FakePane())()

		save_setting.assert_called_once_with(
			'Core Settings.json', 'file_mention_excluded', []
		)

	def test_remove_is_hidden_when_list_is_empty(self):
		with patch(
			'core.commands.file_mention_exclusions.get_setting',
			return_value=[],
		):
			self.assertFalse(IncludeFolderInFileMention(FakePane()).is_visible())
