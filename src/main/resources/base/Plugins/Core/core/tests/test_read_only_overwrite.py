from core.fileoperations import CopyFiles, MoveFiles
from core.tests import StubFS
from core.tests.test_fileoperations import MockProgressDialog
from fman import ABORT, NO, PLATFORM, YES, YES_TO_ALL
from fman.impl.overwrite_dialog import OverwriteChoice
from fman.url import as_url, join
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf
from unittest.mock import patch


@skipIf(PLATFORM != 'Windows', 'Read-only replacement prompt is Windows-specific')
class ReadOnlyOverwriteTest(TestCase):
	def setUp(self):
		self._tmp_dir = TemporaryDirectory()
		self._root = as_url(self._tmp_dir.name)
		self.src = join(self._root, 'src')
		self.dest = join(self._root, 'dest')
		self._fs = StubFS()
		self._fs.makedirs(self.src)
		self._fs.makedirs(self.dest)
		self._dialog = MockProgressDialog(self)

	def tearDown(self):
		for name in ('a.txt', 'b.txt'):
			path = Path(self._path(self.dest, name))
			if path.exists():
				path.chmod(path.stat().st_mode | 0o200)
		self._tmp_dir.cleanup()

	def test_yes_replaces_read_only_target_for_copy_and_move(self):
		for operation in (CopyFiles, MoveFiles):
			with self.subTest(operation=operation.__name__):
				self._reset_files(('a.txt',))
				self._expect_overwrite('a.txt', OverwriteChoice.OVERWRITE)
				self._expect_read_only_question('a.txt', YES)
				self._run(operation, ('a.txt',))
				self.assertEqual('incoming a.txt', self._read_dest('a.txt'))

	def test_no_skips_read_only_target_for_copy_and_move(self):
		for operation in (CopyFiles, MoveFiles):
			with self.subTest(operation=operation.__name__):
				self._reset_files(('a.txt',))
				self._expect_overwrite('a.txt', OverwriteChoice.OVERWRITE)
				self._expect_read_only_question('a.txt', NO)
				self._run(operation, ('a.txt',))
				self.assertEqual('old a.txt', self._read_dest('a.txt'))

	def test_abort_stops_before_copying_later_files(self):
		for operation in (CopyFiles, MoveFiles):
			with self.subTest(operation=operation.__name__):
				self._reset_files(('a.txt', 'b.txt'))
				self._dialog.expect_overwrite(
					'a.txt exists. Do you want to overwrite it?',
					OverwriteChoice.OVERWRITE
				)
				self._expect_read_only_question('a.txt', ABORT)
				self._run(operation, ('a.txt', 'b.txt'))
				self.assertEqual('old a.txt', self._read_dest('a.txt'))
				self.assertEqual('old b.txt', self._read_dest('b.txt'))

	def test_yes_to_all_suppresses_second_read_only_question(self):
		self._reset_files(('a.txt', 'b.txt'))
		self._dialog.expect_overwrite(
			'a.txt exists. Do you want to overwrite it?',
			OverwriteChoice.OVERWRITE_ALL
		)
		self._expect_read_only_question('a.txt', YES_TO_ALL)
		self._run(CopyFiles, ('a.txt', 'b.txt'))
		self.assertEqual('incoming a.txt', self._read_dest('a.txt'))
		self.assertEqual('incoming b.txt', self._read_dest('b.txt'))

	def test_failed_write_after_read_only_confirmation_uses_end_prompt(self):
		self._reset_files(('a.txt',))
		self._expect_overwrite('a.txt', OverwriteChoice.OVERWRITE)
		self._expect_read_only_question('a.txt', YES)
		self._dialog.expect_alert((
			'Copying a.txt: 1 file failed.\n\n'
			'Error copying a.txt (permission denied).\n\nRetry it?',
			YES | NO, YES
		), NO)
		backend = next(iter(self._fs._backends.values()))
		with patch.object(
			backend, 'copy', side_effect=OSError(13, 'permission denied')
		):
			self._run(CopyFiles, ('a.txt',))

	def test_writable_target_has_no_second_question(self):
		self._reset_files(('a.txt',), read_only=False)
		self._dialog.expect_overwrite(
			'a.txt exists. Do you want to overwrite it?',
			OverwriteChoice.OVERWRITE
		)
		self._run(CopyFiles, ('a.txt',))
		self.assertEqual('incoming a.txt', self._read_dest('a.txt'))

	def test_setting_off_replaces_without_second_question(self):
		self._reset_files(('a.txt',))
		self._dialog.expect_overwrite(
			'a.txt exists. Do you want to overwrite it?',
			OverwriteChoice.OVERWRITE
		)
		with patch('core.read_only_overwrite.is_enabled', return_value=False):
			self._run(CopyFiles, ('a.txt',))
		self.assertEqual('incoming a.txt', self._read_dest('a.txt'))

	def _reset_files(self, names, read_only=True):
		for name in ('a.txt', 'b.txt'):
			for folder in (self.src, self.dest):
				path = Path(self._path(folder, name))
				if path.exists():
					path.chmod(path.stat().st_mode | 0o200)
					path.unlink()
		for name in names:
			Path(self._path(self.src, name)).write_text('incoming ' + name)
			dest = Path(self._path(self.dest, name))
			dest.write_text('old ' + name)
			if read_only:
				dest.chmod(dest.stat().st_mode & ~0o200)

	def _expect_read_only_question(self, name, answer):
		self._dialog.expect_alert((
			name + ' is read-only. Do you want to replace it anyway?',
			YES | YES_TO_ALL | NO | ABORT, NO
		), answer)

	def _expect_overwrite(self, name, answer):
		self._dialog.expect_overwrite(
			name + ' exists. Do you want to overwrite it?', answer
		)

	def _run(self, operation, names):
		sources = [join(self.src, name) for name in names]
		task = operation(sources, self.dest, fs=self._fs)
		task._dialog = self._dialog
		task()
		self._dialog.verify_expected_dialogs_were_shown()

	def _read_dest(self, name):
		return Path(self._path(self.dest, name)).read_text()

	@staticmethod
	def _path(folder, name):
		from fman.url import as_human_readable
		return as_human_readable(join(folder, name))
