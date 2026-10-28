from core.commands.transfer import Copy, Move, Symlink, _from_human_readable, \
	get_dest_suggestion
from core.undo_history import CopyRecord, MoveRecord, history
from core.tests import StubUI
from core.util import filenotfounderror
from fman import OK, YES, NO, PLATFORM
from fman.url import join, as_human_readable, as_url
from unittest import TestCase
from unittest.mock import Mock, patch

import os
import os.path

class ConfirmTreeOperationTest(TestCase):

	class FileSystem:
		def __init__(self, files, case_sensitive=PLATFORM == 'Linux'):
			self._files = files
			self._case_sensitive = case_sensitive

		def exists(self, url):
			try:
				self._get(url)
			except KeyError:
				return False
			return True

		def is_dir(self, url):
			try:
				file_info = self._get(url)
			except KeyError:
				raise filenotfounderror(url) from None
			return file_info['is_dir']

		def samefile(self, url1, url2):
			if not self._case_sensitive:
				url1 = url1.lower()
				url2 = url2.lower()
			return url1 == url2

		def iterdir(self, url):
			prefix = url.rstrip('/') + '/'
			return [
				path[len(prefix):] for path in self._files
				if path.startswith(prefix) and '/' not in path[len(prefix):]
			]

		def _get(self, url):
			dict_ = self._files
			if not self._case_sensitive:
				dict_ = {k.lower(): v for k, v in self._files.items()}
				url = url.lower()
			return dict_[url]

	def test_no_files(self):
		self._expect_alert(('No file is selected!',), answer=OK)
		self._check([], None)
	def test_completion_lists_the_destination_directory(self):
		self._fs._files[join(self._dest, 'alpha')] = {'is_dir': True}
		class UI:
			def show_prompt(_, *args, **kwargs):
				self.completion = kwargs['get_completions']
				return 'a', False
		ui = UI()
		Move._confirm_tree_operation([self._a_txt], self._dest, ui, self._fs)
		self.assertEqual(['alpha' + os.sep], self.completion('a'))
	def test_one_file(self):
		self._expect_prompt(self._prompt('a.txt', 0, 1), ('a.txt', True))
		self._check([self._a_txt], (self._dest, 'a.txt'))
	def test_one_file_renamed(self):
		self._expect_prompt(self._prompt('a.txt', 0, 1), ('z.txt', True))
		self._check([self._a_txt], (self._dest, 'z.txt'))
	def test_one_dir(self):
		self._expect_prompt(self._prompt('a', 0, None), ('a', True))
		self._check([self._a], (self._dest, 'a'))
	def test_one_dir_existing_in_dest(self):
		self._fs._files[join(self._dest, 'a')] = {'is_dir': True}
		self._expect_prompt(self._prompt('a', 0, None), ('a', True))
		self._check([self._a], (self._dest, None))
	def test_one_dir_into_itself(self):
		self._expect_prompt(self._prompt('a', 0, None, self._a), ('a', True))
		self._expect_alert(('You cannot move a file to itself!',), answer=OK)
		self._check([self._a], None, dest_dir=self._a)
	def test_rename_dir_to_uppercase(self):
		self._expect_prompt(
			self._prompt('a', 0, None, self._src), ('A', True)
		)
		self._check([self._a], (self._src, 'A'), dest_dir=self._src)
	def test_two_files(self):
		dest_path = as_human_readable(self._dest)
		self._expect_prompt(
			('Move 2 files to', dest_path, 0, None), (dest_path, True)
		)
		self._check([self._a_txt, self._b_txt], (self._dest, None))
	def test_into_subfolder(self):
		sub = join(self._dest, 'sub')
		self._fs._files[sub] = {'is_dir': True}
		self._expect_prompt(self._prompt('a.txt', 0, 1), ('sub', True))
		self._check([self._a_txt], (sub, None))
	def test_overwrite_single_file(self):
		self._fs._files[join(self._dest, 'a.txt')] = {'is_dir': False}
		self._expect_prompt(self._prompt('a.txt', 0, 1), ('a.txt', True))
		self._check([self._a_txt], (self._dest, 'a.txt'))
	def test_multiple_files_over_one(self):
		dest_url = join(self._dest, 'a.txt')
		self._fs._files[dest_url] = {'is_dir': False}
		dest_path = as_human_readable(dest_url)
		self._expect_prompt(
			('Move 2 files to', as_human_readable(self._dest), 0, None),
			(dest_path, True)
		)
		self._expect_alert(
			('You cannot move multiple files to a single file!',), answer=OK
		)
		self._check([self._a_txt, self._b_txt], None)
	def test_multiple_into_self(self):
		dest_path = as_human_readable(self._a)
		self._expect_prompt(
			('Move 2 files to', dest_path, 0, None), (dest_path, True)
		)
		self._expect_alert(('You cannot move a file to itself!',), answer=OK)
		self._check([self._a_txt, self._a], None, dest_dir=self._a)
	def test_absolute_destination(self):
		self._expect_prompt(
			self._prompt('a.txt', 0, 1),
			(as_human_readable(join(self._src, 'z.txt')), True)
		)
		self._check([self._a_txt], (self._src, 'z.txt'))
	def test_multiple_files_nonexistent_dest(self):
		dest_url = join(self._dest, 'dir')
		dest_path = as_human_readable(dest_url)
		self._expect_prompt(
			('Move 2 files to', as_human_readable(self._dest), 0, None),
			(dest_path, True)
		)
		self._expect_alert(
			('%s does not exist. Do you want to create it as a directory and '
			 'move the files there?' % dest_path, YES | NO, YES),
			answer=YES
		)
		self._check([self._a_txt, self._b_txt], (dest_url, None))
	def test_file_system_root(self):
		self._expect_prompt(
			self._prompt('a.txt', 0, 1, self._root), ('a.txt', True)
		)
		self._check([self._a_txt], (self._root, 'a.txt'), dest_dir=self._root)
	def test_different_scheme(self):
		self._expect_prompt(self._prompt('a.txt', 0, 1), ('a.txt', True))
		self._check(['zip:///dest.zip/a.txt'], (self._dest, 'a.txt'))
	def _prompt(self, name, sel_start, sel_end, dest_dir=None):
		message = 'Move "%s" to\n%s' % \
			(name, as_human_readable(dest_dir or self._dest))
		return message, name, sel_start, sel_end
	def _expect_alert(self, args, answer):
		self._ui.expect_alert(args, answer)
	def _expect_prompt(self, args, answer):
		self._ui.expect_prompt(args, answer)
	def _check(self, files, expected_result, dest_dir=None):
		if dest_dir is None:
			dest_dir = self._dest
		actual_result = Move._confirm_tree_operation(
			files, dest_dir, self._ui, self._fs
		)
		self._ui.verify_expected_dialogs_were_shown()
		self.assertEqual(expected_result, actual_result)
	def setUp(self):
		super().setUp()
		self._ui = StubUI(self)
		self._root = as_url('C:\\' if PLATFORM == 'Windows' else '/')
		self._src = join(self._root, 'src')
		self._dest = join(self._root, 'dest')
		self._a = join(self._root, 'src/a')
		self._a_txt = join(self._root, 'src/a.txt')
		self._b_txt = join(self._root, 'src/b.txt')
		self._fs = self.FileSystem({
			self._src: {'is_dir': True},
			self._dest: {'is_dir': True},
			self._a: {'is_dir': True},
			self._a_txt: {'is_dir': False},
			self._b_txt: {'is_dir': False},
		})


class TransferRecordingTest(TestCase):
	_SRC = 'file:///src/a.txt'
	_DEST = 'file:///dest/a.txt'

	def setUp(self):
		history.clear()

	def tearDown(self):
		history.clear()

	def test_move_records_a_successful_destination(self):
		with self._move_command(exists=[False, True]) as command:
			command(files=[self._SRC], dest_dir='file:///dest')
		self.assertEqual(MoveRecord(((self._SRC, self._DEST),)), history.pop())

	def test_copy_records_a_successful_destination(self):
		with self._copy_command(exists=[False, True]) as command:
			command(files=[self._SRC], dest_dir='file:///dest')
		self.assertEqual(CopyRecord(((self._SRC, self._DEST),)), history.pop())

	def test_copy_skips_a_destination_that_existed_before_the_operation(self):
		with self._copy_command(exists=[True]) as command:
			command(files=[self._SRC], dest_dir='file:///dest')
		self.assertIsNone(history.pop())

	def test_symlink_operations_are_not_recorded(self):
		Symlink(Mock())._record_operation(
			((self._SRC, self._DEST),), set()
		)
		self.assertIsNone(history.pop())

	def _move_command(self, exists):
		return self._command(Move, exists)

	def _copy_command(self, exists):
		return self._command(Copy, exists)

	def _command(self, command_type, exists):
		command = command_type(Mock())
		command._confirm_tree_operation = Mock(
			return_value=('file:///dest', None)
		)
		command._call = Mock()
		return _CommandContext(command, exists)


class _CommandContext:
	def __init__(self, command, exists):
		self._command = command
		self._exists = exists
	def __enter__(self):
		self._exists_patch = patch(
			'core.commands.transfer.fman.fs.exists',
			side_effect=self._exists
		)
		self._makedirs_patch = patch('core.commands.transfer.makedirs')
		self._exists_patch.start()
		self._makedirs_patch.start()
		return self._command
	def __exit__(self, *_):
		self._makedirs_patch.stop()
		self._exists_patch.stop()
		return False

class GetDestSuggestionTest(TestCase):
	def test_file(self):
		file_path = os.path.join(self._root, 'file.txt')
		selection_start = file_path.rindex(os.sep) + 1
		selection_end = selection_start + len('file')
		self.assertEqual(
			(file_path, selection_start, selection_end),
			get_dest_suggestion(as_url(file_path))
		)
	def test_dir(self):
		dir_path = os.path.join(self._root, 'dir')
		selection_start = dir_path.rindex(os.sep) + 1
		selection_end = None
		self.assertEqual(
			(dir_path, selection_start, selection_end),
			get_dest_suggestion(as_url(dir_path))
		)
	def setUp(self):
		super().setUp()
		self._root = 'C:\\' if PLATFORM == 'Windows' else '/'

class FromHumanReadableTest(TestCase):
	def test_no_src_dir(self):
		path = __file__
		dir_url = as_url(os.path.dirname(path))
		self.assertEqual(
			as_url(path),
			_from_human_readable(path, dir_url, None)
		)
