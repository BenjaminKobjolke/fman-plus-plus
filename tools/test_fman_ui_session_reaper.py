"""Tests for cleanup and stale-session handling in the UI test reaper."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import session_reaper


class SessionReaperTest(TestCase):
	def test_close_session_kills_process_cleans_recycle_bin_and_removes_folder(self):
		with TemporaryDirectory() as temp:
			session_root = Path(temp) / 'session'
			session_root.mkdir()
			(session_root / session_reaper.SESSION_FILE).write_text(
				json.dumps({'pid': 123, 'start_time': 4.5}), encoding='utf-8')
			with patch.object(session_reaper, 'kill_process') as kill_process, \
				patch.object(session_reaper, 'cleanup_session', return_value=3):
				removed = session_reaper.close_session(session_root)
			kill_process.assert_called_once_with(123, 4.5)
			self.assertEqual(3, removed)
			self.assertFalse(session_root.exists())

	def test_close_session_kills_fman_child_instead_of_exited_launcher(self):
		with TemporaryDirectory() as temp:
			session_root = Path(temp) / 'session'
			session_root.mkdir()
			(session_root / session_reaper.SESSION_FILE).write_text(json.dumps({
				'pid': 123, 'start_time': 4.5,
				'fman_pid': 456, 'fman_start_time': 6.5,
			}), encoding='utf-8')
			with patch.object(session_reaper, 'kill_process') as kill_process, \
				patch.object(session_reaper, 'cleanup_session', return_value=0):
				session_reaper.close_session(session_root)
			kill_process.assert_called_once_with(456, 6.5)

	def test_close_session_removes_folder_when_recycle_cleanup_fails(self):
		with TemporaryDirectory() as temp:
			session_root = Path(temp) / 'session'
			session_root.mkdir()
			(session_root / session_reaper.SESSION_FILE).write_text(
				json.dumps({'pid': 123, 'start_time': 4.5}), encoding='utf-8')
			with patch.object(session_reaper, 'kill_process') as kill_process, \
				patch.object(session_reaper, 'cleanup_session',
					side_effect=OSError('Recycle Bin unavailable')):
				self.assertEqual(0, session_reaper.close_session(session_root))
			kill_process.assert_called_once_with(123, 4.5)
			self.assertFalse(session_root.exists())

	def test_kill_process_kills_children_then_parent_for_matching_start_time(self):
		calls = []
		child = Mock()
		child.kill.side_effect = lambda: calls.append('child')
		parent = Mock()
		parent.create_time.return_value = 10
		parent.children.return_value = [child]
		parent.kill.side_effect = lambda: calls.append('parent')
		process_class = Mock(return_value=parent)
		with patch.object(session_reaper.psutil, 'Process', process_class), \
			patch.object(session_reaper.psutil, 'wait_procs') as wait_procs:
			session_reaper.kill_process(123, 10)
		self.assertEqual(['child', 'parent'], calls)
		wait_procs.assert_called_once_with([child, parent], timeout=5)

	def test_kill_process_ignores_reused_pid_and_missing_process(self):
		process = Mock()
		process.create_time.return_value = 20
		with patch.object(session_reaper.psutil, 'Process', return_value=process):
			session_reaper.kill_process(123, 10)
		process.kill.assert_not_called()
		process.children.assert_not_called()
		with patch.object(session_reaper.psutil, 'Process',
				side_effect=session_reaper.psutil.NoSuchProcess(123)):
			session_reaper.kill_process(123, 10)

	def test_is_stale_checks_session_age_and_process_identity(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			session_file = root / session_reaper.SESSION_FILE
			session_file.write_text(json.dumps({'pid': 1, 'start_time': 10}))
			with patch.object(session_reaper.psutil, 'Process') as process_class:
				process_class.return_value.create_time.return_value = 10
				self.assertFalse(session_reaper.is_stale(root, 100))
				with patch.object(Path, 'stat') as stat:
					stat.return_value.st_mtime = (
						100 - session_reaper.IDLE_LIMIT_SECONDS - 1)
					self.assertTrue(session_reaper.is_stale(root, 100))
					stat.return_value.st_mtime = 100
					process_class.side_effect = session_reaper.psutil.NoSuchProcess(1)
					self.assertTrue(session_reaper.is_stale(root, 100))
					process_class.side_effect = None
					process_class.return_value.create_time.return_value = 12
					self.assertTrue(session_reaper.is_stale(root, 100))

	def test_is_stale_checks_fman_child_when_launcher_has_exited(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			(root / session_reaper.SESSION_FILE).write_text(json.dumps({
				'pid': 1, 'start_time': 10,
				'fman_pid': 2, 'fman_start_time': 20,
			}), encoding='utf-8')
			now = session_reaper.time.time()
			process = Mock(create_time=Mock(return_value=20))
			with patch.object(session_reaper.psutil, 'Process',
					return_value=process) as process_class:
				self.assertFalse(session_reaper.is_stale(root, now))
			self.assertEqual([2], [call.args[0] for call in
				process_class.call_args_list])

	def test_is_stale_uses_folder_mtime_without_session_file(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			with patch.object(Path, 'stat') as stat:
				stat.return_value.st_mtime = 100
				self.assertFalse(session_reaper.is_stale(root, 100))
				stat.return_value.st_mtime = 1
				self.assertTrue(session_reaper.is_stale(root, 1 +
					session_reaper.IDLE_LIMIT_SECONDS + 1))

	def test_is_stale_honors_fresh_restart_marker_only_within_grace_period(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			(root / session_reaper.SESSION_FILE).write_text(
				json.dumps({'pid': 1, 'start_time': 10}))
			marker = root / session_reaper.RESTART_MARKER
			marker.write_text('')
			with patch.object(Path, 'stat') as stat, \
				patch.object(session_reaper.psutil, 'Process',
					side_effect=session_reaper.psutil.NoSuchProcess(1)):
				stat.return_value.st_mtime = 100
				self.assertFalse(session_reaper.is_stale(root, 100))
				stat.return_value.st_mtime = (
					100 - session_reaper.RESTART_GRACE_SECONDS - 1)
				self.assertTrue(session_reaper.is_stale(root, 100))

	def test_reap_stale_closes_only_stale_folders(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			stale, fresh = root / 'stale', root / 'fresh'
			stale.mkdir()
			fresh.mkdir()
			(root / 'current.json').write_text('{}')
			with patch.object(session_reaper, 'is_stale',
					side_effect=lambda path, now: path == stale), \
				patch.object(session_reaper, 'close_session') as close:
				session_reaper.reap_stale(root, 100)
		close.assert_called_once_with(stale)

	def test_watch_closes_stale_session_and_returns_when_folder_disappears(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			root.mkdir()
			with patch.object(session_reaper, 'is_stale', return_value=True), \
				patch.object(session_reaper, 'close_session') as close, \
				patch.object(session_reaper.time, 'sleep'):
				session_reaper.watch(root)
			close.assert_called_once_with(root)
			gone = root.parent / 'gone'
			gone.mkdir()
			with patch.object(session_reaper.time, 'sleep',
					side_effect=lambda _seconds: gone.rmdir()), \
				patch.object(session_reaper, 'close_session') as close:
				session_reaper.watch(gone)
			close.assert_not_called()


if __name__ == '__main__':
	from unittest import main
	main()
