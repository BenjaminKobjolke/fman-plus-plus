from fman import DirectoryPane, DirectoryPaneCommand, DirectoryPaneListener
from unittest import TestCase
from unittest.mock import Mock


class RewriteCommandTest(TestCase):
	def setUp(self):
		self.pane = DirectoryPane(None, None, Mock())

	def test_returns_listener_rewrite(self):
		args = {'urls': ['ftp://host/file.txt']}

		class RewriteListener(DirectoryPaneListener):
			def on_command(self, name, args):
				if name == 'move_to_trash':
					return 'delete_permanently', args

		self.pane._add_listener(RewriteListener(self.pane))

		self.assertEqual(
			('delete_permanently', args),
			self.pane._rewrite_command('move_to_trash', args)
		)

	def test_returns_original_command_when_no_listener_rewrites_it(self):
		args = {'urls': ['file:///file.txt']}
		self.pane._add_listener(DirectoryPaneListener(self.pane))

		self.assertEqual(
			('move_to_trash', args),
			self.pane._rewrite_command('move_to_trash', args)
		)


class ChosenFilesTest(TestCase):
	def setUp(self):
		self.widget = Mock()
		self.pane = DirectoryPane(None, self.widget, Mock())

	def test_selected_files_win_over_file_under_cursor(self):
		self.widget.get_selected_files.return_value = ['file:///a', 'file:///b']
		self.widget.get_file_under_cursor.return_value = 'file:///cursor'

		self.assertEqual(['file:///a', 'file:///b'], self.pane.get_chosen_files())

	def test_file_under_cursor_is_used_when_nothing_is_selected(self):
		self.widget.get_selected_files.return_value = []
		self.widget.get_file_under_cursor.return_value = 'file:///cursor'

		self.assertEqual(['file:///cursor'], self.pane.get_chosen_files())

	def test_no_selection_or_cursor_returns_empty_list(self):
		self.widget.get_selected_files.return_value = []
		self.widget.get_file_under_cursor.return_value = None

		self.assertEqual([], self.pane.get_chosen_files())

	def test_command_and_pane_return_same_selected_files(self):
		self.widget.get_selected_files.return_value = ['file:///a']
		self.widget.get_file_under_cursor.return_value = 'file:///cursor'

		self.assertEqual(
			self.pane.get_chosen_files(),
			DirectoryPaneCommand(self.pane).get_chosen_files()
		)

	def test_command_supports_duck_typed_pane(self):
		class Pane:
			def get_selected_files(self):
				return []

			def get_file_under_cursor(self):
				return 'file:///cursor'

		self.assertEqual(
			['file:///cursor'],
			DirectoryPaneCommand(Pane()).get_chosen_files()
		)

