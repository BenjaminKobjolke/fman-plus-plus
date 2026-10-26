from core import LocalFileSystem
from core.move_rollback import MoveRollback
from fman.url import as_url
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase


class MoveRollbackTest(TestCase):

	def setUp(self):
		self._fs = LocalFileSystem()

	def test_same_drive_move_task_exposes_rollback_urls(self):
		with TemporaryDirectory() as tmp_dir:
			root = Path(tmp_dir)
			source = root / 'source.txt'
			source.write_text('moved')
			destination = root / 'destination'
			destination.mkdir()
			task = next(self._fs.prepare_move(
				as_url(source), as_url(destination / source.name)
			))
			self.assertEqual((as_url(source), as_url(destination / source.name)),
				task.moved_urls)

	def test_restores_file_into_recreated_source_parent(self):
		with TemporaryDirectory() as tmp_dir:
			root = Path(tmp_dir)
			source = root / 'missing' / 'parent' / 'file.txt'
			destination = root / 'destination.txt'
			destination.write_text('moved')
			rollback = MoveRollback()
			rollback.record(_move(as_url(source), as_url(destination)))

			failed = rollback.run(self._fs)

			self.assertEqual([], failed)
			self.assertEqual('moved', source.read_text())
			self.assertFalse(destination.exists())

	def test_restores_renamed_folder(self):
		with TemporaryDirectory() as tmp_dir:
			root = Path(tmp_dir)
			source = root / 'source'
			destination = root / 'destination'
			destination.mkdir()
			(destination / 'file.txt').write_text('moved')
			rollback = MoveRollback()
			rollback.record(_move(as_url(source), as_url(destination)))

			failed = rollback.run(self._fs)

			self.assertEqual([], failed)
			self.assertTrue((source / 'file.txt').exists())
			self.assertFalse(destination.exists())

	def test_leaves_move_when_source_is_occupied(self):
		with TemporaryDirectory() as tmp_dir:
			root = Path(tmp_dir)
			source = root / 'source.txt'
			destination = root / 'destination.txt'
			source.write_text('new source')
			destination.write_text('moved')
			rollback = MoveRollback()
			rollback.record(_move(as_url(source), as_url(destination)))

			failed = rollback.run(self._fs)

			self.assertEqual([as_url(destination)], failed)
			self.assertEqual('new source', source.read_text())
			self.assertEqual('moved', destination.read_text())

	def test_removes_empty_new_destination_folders(self):
		with TemporaryDirectory() as tmp_dir:
			root = Path(tmp_dir)
			destination = root / 'new' / 'nested'
			destination.mkdir(parents=True)
			rollback = MoveRollback()
			rollback.add_new_destination(as_url(root / 'new'))

			failed = rollback.run(self._fs)

			self.assertEqual([], failed)
			self.assertFalse((root / 'new').exists())

	def test_preserves_new_destination_folder_with_foreign_file(self):
		with TemporaryDirectory() as tmp_dir:
			root = Path(tmp_dir)
			destination = root / 'new'
			destination.mkdir()
			foreign = destination / 'foreign.txt'
			foreign.write_text('keep')
			rollback = MoveRollback()
			rollback.add_new_destination(as_url(destination))

			failed = rollback.run(self._fs)

			self.assertEqual([], failed)
			self.assertEqual('keep', foreign.read_text())


def _move(source_url, destination_url):
	return SimpleNamespace(moved_urls=(source_url, destination_url))
