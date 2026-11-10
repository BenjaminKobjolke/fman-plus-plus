from core.commands.rename import CreateDirectory
from fman import DirectoryPane
from unittest import TestCase
from unittest.mock import MagicMock, patch


class CreateDirectoryTest(TestCase):
	def test_prompt_starts_empty(self):
		pane = MagicMock(spec=DirectoryPane)
		pane.get_file_under_cursor.return_value = (
			'file://C:/dir/report.final.txt'
		)
		pane.get_path.return_value = 'file://C:/dir'

		with patch(
			'core.commands.rename.show_input', return_value=None
		) as show_input, patch('core.commands.rename.makedirs') as makedirs:
			CreateDirectory(pane)()

		show_input.assert_called_once_with('New folder (directory)')
		makedirs.assert_not_called()
