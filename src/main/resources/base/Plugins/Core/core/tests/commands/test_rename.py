from core.commands.rename import _Rename, rename_to
from core.undo_history import RenameRecord, history
from core.tests import StubUI
from fman import CANCEL, RETRY, Task
# Not in fman's __all__, so it isn't part of the star import Core uses:
from fman import DirectoryPane
from unittest import TestCase
from unittest.mock import MagicMock, patch

class RenameTest(TestCase):

	"""
	A failed rename must not throw away the name the user typed: the alert
	offers Retry, which re-attempts the very same rename (see #_Rename).
	"""

	_SRC = 'file://C:/dir/a'
	_DST = 'file://C:/dir/b'
	_ALERT = (
		'Access was denied trying to rename a to b.', RETRY | CANCEL, RETRY
	)

	def test_retry_reruns_the_move(self):
		self._expect_alert(answer=RETRY)
		self._rename()
		self.assertEqual([(self._SRC, self._DST)] * 2, self._prepared)
		self._pane.place_cursor_at.assert_called_once_with(self._DST)
		self.assertEqual(
			RenameRecord(((self._SRC, self._DST),)), history.pop()
		)
	def test_cancel_gives_up(self):
		self._expect_alert(answer=CANCEL)
		self._rename()
		self.assertEqual([(self._SRC, self._DST)], self._prepared)
		self._pane.place_cursor_at.assert_not_called()
		self.assertIsNone(history.pop())
	def test_escape_gives_up(self):
		# MessageBox lets Escape through, which returns 0 rather than a button.
		self._expect_alert(answer=0)
		self._rename()
		self.assertEqual([(self._SRC, self._DST)], self._prepared)
		self._pane.place_cursor_at.assert_not_called()
		self.assertIsNone(history.pop())
	def test_case_only_rename_is_recorded(self):
		with patch('core.commands.rename.exists', return_value=True), \
				patch('core.commands.rename.samefile', return_value=True), \
				patch('core.commands.rename.elevation.rename', return_value=True):
			result = rename_to(
				self._pane, 'file://C:/dir/Foo', 'foo'
			)
		self.assertEqual('file://C:/dir/foo', result)
		self.assertEqual(
			RenameRecord((('file://C:/dir/Foo', 'file://C:/dir/foo'),)),
			history.pop()
		)
	def setUp(self):
		super().setUp()
		self._prepared = []
		self._dialog = _StubProgressDialog(self)
		self._pane = MagicMock(spec=DirectoryPane)
		history.clear()
	def tearDown(self):
		history.clear()
	def _expect_alert(self, answer):
		self._dialog.expect_alert(self._ALERT, answer)
	def _rename(self):
		task = _Rename(self._pane, self._SRC, self._DST)
		task._dialog = self._dialog
		with patch('core.commands.rename.prepare_move', self._prepare_move):
			task()
		self._dialog.verify_expected_dialogs_were_shown()
	def _prepare_move(self, src_url, dst_url):
		self._prepared.append((src_url, dst_url))
		# Only the first attempt fails - a Retry must then succeed:
		fails = len(self._prepared) == 1
		yield Task('Moving a', size=1, fn=self._move, args=(fails,))
	def _move(self, fails):
		if fails:
			raise PermissionError()

class _StubProgressDialog(StubUI):

	"""
	StubUI's alert queue plus the progress-dialog methods Task calls on
	#_dialog. Tasks are given one by fman.submit_task(...), which tests skip.
	"""

	def __init__(self, test_case):
		super().__init__(test_case)
		self._progress = 0
	def set_text(self, text):
		pass
	def set_task_size(self, size):
		pass
	def get_progress(self):
		return self._progress
	def set_progress(self, progress):
		self._progress = progress
	def was_canceled(self):
		return False
