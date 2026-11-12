from fman import DirectoryPane, DirectoryPaneCommand, DirectoryPaneListener
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import Mock


_app = QApplication.instance() or QApplication([])


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
		self.widget._mounted_widget = None
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

	def test_mounted_widget_supplies_cursor_and_chosen_files(self):
		class MountedWidget:
			def get_file_under_cursor(self):
				return 'file:///mounted'

		class PaneWidget:
			_mounted_widget = MountedWidget()

			def get_selected_files(self):
				return []

			def get_file_under_cursor(self):
				return 'file:///list'

		pane = DirectoryPane(None, PaneWidget(), Mock())

		self.assertEqual('file:///mounted', pane.get_file_under_cursor())
		self.assertEqual(['file:///mounted'], pane.get_chosen_files())

	def test_mounted_widget_methods_fall_back_individually(self):
		class MountedWidget:
			pass

		class PaneWidget:
			_mounted_widget = MountedWidget()

			def get_selected_files(self):
				return ['file:///selected']

			def get_file_under_cursor(self):
				return 'file:///list'

			def place_cursor_at(self, url):
				self.placed_url = url

			def get_location(self):
				return 'file:///location'

		widget = PaneWidget()
		pane = DirectoryPane(None, widget, Mock())

		self.assertEqual(['file:///selected'], pane.get_selected_files())
		self.assertEqual('file:///list', pane.get_file_under_cursor())
		self.assertEqual('file:///location', pane.get_path())
		pane.place_cursor_at('file:///target')
		self.assertEqual('file:///target', widget.placed_url)

	def test_mounted_widget_with_no_location_uses_mounted_location(self):
		class MountedWidget:
			def get_location(self):
				return None

		class PaneWidget:
			_mounted_widget = MountedWidget()

			def get_location(self):
				return 'file:///location'

		pane = DirectoryPane(None, PaneWidget(), Mock())

		self.assertIsNone(pane.get_path())

	def test_nothing_mounted_uses_file_list(self):
		widget = Mock()
		widget._mounted_widget = None
		widget.get_selected_files.return_value = ['file:///selected']
		widget.get_file_under_cursor.return_value = 'file:///list'
		widget.get_location.return_value = 'file:///location'
		pane = DirectoryPane(None, widget, Mock())

		self.assertEqual(['file:///selected'], pane.get_selected_files())
		self.assertEqual('file:///list', pane.get_file_under_cursor())
		self.assertEqual('file:///location', pane.get_path())

