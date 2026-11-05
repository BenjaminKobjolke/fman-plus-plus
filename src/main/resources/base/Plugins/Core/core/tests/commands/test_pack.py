from core.commands.pack import _suggest_archive_name, PackWithPassword
from core.fs import archive_password
from fman import YES
from unittest import TestCase
from unittest.mock import DEFAULT, MagicMock, patch

class SuggestArchiveNameTest(TestCase):

	"""
	The name Pack suggests when several files are chosen: the pane's directory.
	A drive root has no directory name - 'C:.zip' is not a valid file name.
	"""

	def test_drive_root(self):
		self.assertEqual('C.zip', _suggest_archive_name('file://C:'))
	def test_drive_root_with_trailing_slash(self):
		self.assertEqual('C.zip', _suggest_archive_name('file://C:/'))
	def test_directory(self):
		self.assertEqual('reports.zip', _suggest_archive_name('file://C:/reports'))
	def test_directory_with_trailing_slash(self):
		self.assertEqual(
			'reports.zip', _suggest_archive_name('file://C:/reports/')
		)
	def test_network_share(self):
		self.assertEqual(
			'share.zip', _suggest_archive_name('file:////server/share')
		)
	def test_unix_root(self):
		self.assertEqual('archive.zip', _suggest_archive_name('file:///'))
	def test_nameless_root(self):
		self.assertEqual('archive.zip', _suggest_archive_name('drives://'))
	def test_directory_inside_archive(self):
		self.assertEqual(
			'folder.zip', _suggest_archive_name('zip://C:/source.zip/folder')
		)


class PackWithPasswordTest(TestCase):
	def setUp(self):
		archive_password.clear()
		self.pane = MagicMock()
		self.pane.get_path.return_value = 'file://C:/source'
		self.pane.get_file_under_cursor.return_value = 'file://C:/source/a.txt'
		self.command = PackWithPassword(self.pane)
		self.patches = patch.multiple(
			'core.commands.pack',
			_get_handler_for_archive=DEFAULT,
			chosen_files=DEFAULT,
			get_opposite_pane=DEFAULT,
			show_prompt=DEFAULT,
			show_alert=DEFAULT,
			mkdir=DEFAULT,
			submit_task=DEFAULT,
		)
		self.mocks = self.patches.start()
		self.mocks['_get_handler_for_archive'].return_value = '7z://'
		self.mocks['chosen_files'].return_value = ['file://C:/source/a.txt']
		self.mocks['show_alert'].return_value = YES
		self.mocks['get_opposite_pane'].return_value.get_path.return_value = \
			'file://C:/dest'
		self.mocks['show_prompt'].side_effect = [
			('file://C:/dest/archive.7z', True),
			('secret', True),
			('secret', True),
		]
	def tearDown(self):
		self.patches.stop()
		archive_password.clear()
	def _run(self, destination, password='secret', confirmation='secret'):
		self.mocks['show_prompt'].side_effect = [
			(destination, True), (password, True), (confirmation, True)
		]
		self.command()
	def test_mismatched_passwords_abort_packing(self):
		self._run('file://C:/dest/archive.7z', confirmation='different')
		self.mocks['show_alert'].assert_called_once()
		self.mocks['mkdir'].assert_not_called()
		self.mocks['submit_task'].assert_not_called()
	def test_tar_is_refused(self):
		self._run('file://C:/dest/archive.tar')
		self.mocks['show_alert'].assert_called_once()
		self.mocks['mkdir'].assert_not_called()
		self.mocks['submit_task'].assert_not_called()
	def test_non_ascii_zip_is_refused(self):
		self._run('file://C:/dest/archive.zip', password='café', confirmation='café')
		self.mocks['show_alert'].assert_called_once()
		self.mocks['mkdir'].assert_not_called()
		self.mocks['submit_task'].assert_not_called()
	def test_non_ascii_7z_password_is_remembered(self):
		self._run('file://C:/dest/archive.7z', password='café', confirmation='café')
		self.mocks['mkdir'].assert_called_once_with('7z://C:/dest/archive.7z')
		self.mocks['submit_task'].assert_called_once()
		self.assertEqual(
			'café', archive_password.get_password('C:/dest/archive.7z')
		)
		self.assertTrue(all(
			call.kwargs.get('password') is True
			for call in self.mocks['show_prompt'].call_args_list[1:]
		))
	def test_canceling_password_prompt_stops_packing(self):
		self.mocks['show_prompt'].side_effect = [
			('file://C:/dest/archive.7z', True), ('', False)
		]
		self.command()
		self.mocks['mkdir'].assert_not_called()
		self.mocks['submit_task'].assert_not_called()
