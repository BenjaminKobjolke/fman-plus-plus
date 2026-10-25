from contextlib import ExitStack
from core import elevation
from core.commands.deletion import DeletePermanently, trash
from core.commands.editor import CreateAndEditFile, OpenWithEditor
from core.commands.rename import CreateDirectory, rename_to
from core.commands.transfer import Copy, Move
# Not in fman's __all__, so it isn't part of the star import Core uses:
from fman import DirectoryPane, YES
from fman.url import as_url, join
from os.path import dirname
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

_DIR = 'file://C:/Program Files/App'
_FILE = _DIR + '/a.txt'

class NeedsElevationTest(TestCase):
	def test_writable_dir(self):
		with TemporaryDirectory() as tmp_dir:
			self.assertFalse(elevation.needs_elevation(as_url(tmp_dir)))
	def test_protected_dir(self):
		with TemporaryDirectory() as tmp_dir:
			with patch('core.elevation.os.open', side_effect=PermissionError):
				self.assertTrue(elevation.needs_elevation(as_url(tmp_dir)))
	def test_one_protected_dir_is_enough(self):
		with TemporaryDirectory() as tmp_dir:
			url = as_url(tmp_dir)
			with patch('core.elevation._is_writable', side_effect=[True, False]):
				self.assertTrue(elevation.needs_elevation(url, url))
	def test_missing_dir_probes_nearest_existing_ancestor(self):
		probed = []
		def open_(path, flags):
			probed.append(dirname(path))
			raise PermissionError()
		with TemporaryDirectory() as tmp_dir:
			missing = join(as_url(tmp_dir), 'a', 'b')
			with patch('core.elevation.os.open', open_):
				self.assertTrue(elevation.needs_elevation(missing))
			self.assertEqual([tmp_dir], probed)
	def test_other_scheme(self):
		self.assertFalse(elevation.needs_elevation('zip://C:/a.zip'))
	def test_other_platform(self):
		with patch('core.elevation.PLATFORM', 'Mac'), \
			patch('core.elevation._is_writable', return_value=False):
			self.assertFalse(elevation.needs_elevation(_DIR))

class _PatchingTest(TestCase):
	def _patch(self, target, *args, **kwargs):
		patcher = patch(target, *args, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

class OperationsTest(_PatchingTest):

	"""
	What each operation queues on the shell's IFileOperation. #_perform - the
	only part that talks to COM and raises the UAC prompt - is replaced by one
	that runs the queue function against a mock.
	"""

	def test_copy(self):
		self.assertTrue(elevation.copy(['file://C:/src/a.txt'], _DIR))
		self._op.CopyItem.assert_called_once_with(
			'C:\\src\\a.txt', 'C:\\Program Files\\App', None
		)
	def test_copy_from_other_scheme_is_not_handled(self):
		self.assertFalse(elevation.copy(['zip://C:/a.zip/a.txt'], _DIR))
		self._op.CopyItem.assert_not_called()
	def test_copy_out_of_protected_dir_is_not_handled(self):
		# Reading needs no rights - only the destination is probed.
		self._protected.side_effect = lambda *urls: _DIR in urls
		self.assertFalse(elevation.copy([_FILE], 'file://C:/dst'))
	def test_move_out_of_protected_dir(self):
		self._protected.side_effect = lambda *urls: _DIR in urls
		self.assertTrue(elevation.move([_FILE], 'file://C:/dst', 'b.txt'))
		self._op.MoveItem.assert_called_once_with(
			'C:\\Program Files\\App\\a.txt', 'C:\\dst', 'b.txt'
		)
	def test_delete(self):
		self.assertTrue(elevation.delete([_FILE], to_trash=False))
		self._op.DeleteItem.assert_called_once_with(
			'C:\\Program Files\\App\\a.txt'
		)
	def test_rename(self):
		self.assertTrue(elevation.rename(_FILE, 'b.txt'))
		self._op.RenameItem.assert_called_once_with(
			'C:\\Program Files\\App\\a.txt', 'b.txt'
		)
	def test_create_file(self):
		self.assertTrue(elevation.create(_FILE, is_dir=False))
		(folder, _, name, *_), _ = self._op.NewItem.call_args
		self.assertEqual(('C:\\Program Files\\App', 'a.txt'), (folder, name))
	def test_create_declined(self):
		self._succeeds = False
		self.assertFalse(elevation.create(_FILE, is_dir=False))
	def test_create_other_scheme_is_not_handled(self):
		with patch('core.elevation.lexists', return_value=False):
			self.assertFalse(
				elevation.create('ftp://host/dir/a.txt', is_dir=False)
			)
		self._op.NewItem.assert_not_called()
	def test_create_stops_at_root(self):
		with patch('core.elevation.lexists', return_value=False):
			self.assertFalse(elevation.create(_FILE, is_dir=False))
		self._op.NewItem.assert_not_called()
	def test_not_needed(self):
		self._protected.return_value = False
		self.assertFalse(elevation.delete([_FILE], to_trash=True))
		self.assertFalse(elevation.rename(_FILE, 'b.txt'))
		self.assertFalse(elevation.move([_FILE], 'file://C:/dst'))
	def setUp(self):
		super().setUp()
		self._op = MagicMock()
		self._succeeds = True
		elevation_ = 'core.elevation.'
		self._protected = \
			self._patch(elevation_ + 'needs_elevation', return_value=True)
		self._patch(elevation_ + '_perform', self._perform)
		self._patch(elevation_ + '_notify')
		self._patch(elevation_ + 'lexists', return_value=True)
	def _perform(self, queue, flags=0):
		queue(self._op, lambda path: path)
		return self._succeeds

class CommandHooksTest(_PatchingTest):

	"""
	Each command hands over to core.elevation when it reports the operation as
	handled, and otherwise carries on exactly as before.
	"""

	def test_copy_elevated(self):
		self._run_transfer(Copy, 'copy', handled=True)
		self._makedirs.assert_not_called()
		self._submit_task.assert_not_called()
	def test_copy_normal(self):
		self._run_transfer(Copy, 'copy', handled=False)
		self._makedirs.assert_called_once_with('file://C:/dst', exist_ok=True)
		self._submit_task.assert_called_once()
	def test_move_elevated(self):
		self._run_transfer(Move, 'move', handled=True)
		self._submit_task.assert_not_called()
	def test_trash_elevated(self):
		with self._elevation('delete', True) as delete:
			trash([_FILE])
		delete.assert_called_once_with([_FILE], to_trash=True)
		self._submit_task.assert_not_called()
	def test_trash_normal(self):
		with self._elevation('delete', False):
			trash([_FILE])
		self._submit_task.assert_called_once()
	def test_delete_permanently_elevated(self):
		with self._elevation('delete', True) as delete, \
			patch('core.commands.deletion.show_alert', return_value=YES):
			DeletePermanently(self._pane)([_FILE])
		delete.assert_called_once_with([_FILE], to_trash=False)
		self._submit_task.assert_not_called()
	def test_rename_elevated(self):
		with self._elevation('rename', True) as rename, \
			patch('core.commands.rename.exists', return_value=False):
			self.assertEqual(_DIR + '/b.txt', rename_to(self._pane, _FILE, 'b.txt'))
		rename.assert_called_once_with(_FILE, 'b.txt')
		self._pane.place_cursor_at.assert_called_once_with(_DIR + '/b.txt')
		self._submit_task.assert_not_called()
	def test_create_directory_elevated(self):
		with self._elevation('create', True) as create, \
			patch('core.commands.rename.show_prompt', return_value=('new', True)), \
			patch('core.commands.rename.makedirs', side_effect=PermissionError):
			CreateDirectory(self._pane)()
		create.assert_called_once_with(_DIR + '/new', is_dir=True)
		self._pane.place_cursor_at.assert_called_once_with(_DIR + '/new')
	def test_create_directory_declined(self):
		with self._elevation('create', False), \
			patch('core.commands.rename.show_prompt', return_value=('new', True)), \
			patch('core.commands.rename.makedirs', side_effect=PermissionError), \
			patch('core.commands.util.show_alert') as show_alert:
			CreateDirectory(self._pane)()
		show_alert.assert_called_once()
		self._pane.place_cursor_at.assert_not_called()
	def test_create_directory_on_other_scheme(self):
		self._pane.get_path.return_value = 'ftp://host/dir'
		with self._elevation('create', False) as create, \
			patch('core.commands.rename.show_prompt', return_value=('new', True)), \
			patch(
				'core.commands.rename.makedirs',
				side_effect=PermissionError('denied')
			), \
			patch('core.commands.util.show_alert') as show_alert:
			CreateDirectory(self._pane)()
		create.assert_not_called()
		show_alert.assert_called_once()
		message = show_alert.call_args[0][0]
		self.assertIn('ftp://host/dir/new', message)
		self.assertIn('denied', message)
		self._pane.place_cursor_at.assert_not_called()
	def test_create_file_elevated(self):
		with self._elevation('create', True) as create, \
			self._new_file_prompt(), \
			patch.object(OpenWithEditor, '__call__') as edit:
			CreateAndEditFile(self._pane)()
		create.assert_called_once_with(_DIR + '/new.txt', is_dir=False)
		edit.assert_called_once_with(_DIR + '/new.txt')
	def test_create_file_declined(self):
		with self._elevation('create', False), \
			self._new_file_prompt(), \
			patch('core.commands.util.show_alert') as show_alert, \
			patch.object(OpenWithEditor, '__call__') as edit:
			CreateAndEditFile(self._pane)()
		show_alert.assert_called_once()
		edit.assert_not_called()
	def test_create_file_on_other_scheme(self):
		self._pane.get_path.return_value = 'ftp://host/dir'
		with self._elevation('create', False) as create, \
			self._new_file_prompt(error=PermissionError('denied')), \
			patch('core.commands.util.show_alert') as show_alert, \
			patch.object(OpenWithEditor, '__call__') as edit:
			CreateAndEditFile(self._pane)()
		create.assert_not_called()
		show_alert.assert_called_once()
		message = show_alert.call_args[0][0]
		self.assertIn('ftp://host/dir/new.txt', message)
		self.assertIn('denied', message)
		edit.assert_not_called()
	def setUp(self):
		super().setUp()
		self._pane = MagicMock(spec=DirectoryPane)
		self._pane.get_path.return_value = _DIR
		self._pane.get_file_under_cursor.return_value = None
		self._submit_task = MagicMock()
		for module in ('deletion', 'rename', 'transfer'):
			self._patch(
				'core.commands.%s.submit_task' % module, self._submit_task
			)
		self._makedirs = self._patch('core.commands.transfer.makedirs')
		self._patch('core.commands.transfer.fman.fs.exists', return_value=False)
		self._patch('core.commands.deletion.exists', return_value=True)
	def _elevation(self, function, handled):
		return patch('core.elevation.' + function, return_value=handled)
	def _new_file_prompt(self, error=PermissionError):
		editor = 'core.commands.editor.'
		result = ExitStack()
		result.enter_context(
			patch(editor + 'show_prompt', return_value=('new.txt', True))
		)
		result.enter_context(patch(editor + 'exists', return_value=False))
		result.enter_context(
			patch(editor + 'touch', side_effect=error)
		)
		return result
	def _run_transfer(self, command_cls, function, handled):
		files = ['file://C:/src/a.txt']
		confirm = patch.object(
			command_cls, '_confirm_tree_operation',
			return_value=('file://C:/dst', None)
		)
		with self._elevation(function, handled) as elevated, confirm:
			command_cls(self._pane)(files=files, dest_dir='file://C:/dst')
		elevated.assert_called_once_with(files, 'file://C:/dst', None)
