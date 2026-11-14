"""Tests for recycle-bin cleanup scoped to an automation session."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import recycle_cleanup


class RecycleCleanupTest(TestCase):
	def test_recycle_cleanup_removes_only_entries_within_session_root(self):
		root = r'C:\Temp\fman-ui\session'
		entries = [
			SimpleNamespace(original_path=r'c:\temp\fman-ui\SESSION\left\visible.txt'),
			SimpleNamespace(original_path=r'C:\Temp\fman-ui\session\right\visible.txt'),
			SimpleNamespace(original_path=r'C:\Temp\fman-ui\session-elsewhere\file.txt'),
			SimpleNamespace(original_path=r'D:\Temp\fman-ui\session\file.txt'),
		]
		remove = Mock(side_effect=[OSError('locked'), None])
		bin_module = SimpleNamespace(
			iter_entries=Mock(return_value=entries), remove_entry=remove)
		with patch.object(recycle_cleanup, '_is_windows', return_value=True), \
			patch.object(recycle_cleanup, '_load_recycle_bin',
				return_value=bin_module):
			removed = recycle_cleanup.cleanup_session(root)
		self.assertEqual(1, removed)
		self.assertEqual(
			[(entries[0],), (entries[1],)],
			[call.args for call in remove.call_args_list],
		)
		self.assertEqual(2, remove.call_count)


if __name__ == '__main__':
	from unittest import main
	main()
