from core.commands.opening import (
	OpenDirectory, OpenOrView, ViewFile, ViewFileInOtherPane, _open_local_files_win,
)
from core.tests.commands import FakePane, FakeWindow
from fman import PLATFORM
from fman.url import as_url
from tempfile import NamedTemporaryFile
from unittest import TestCase, skipUnless
from unittest.mock import MagicMock, patch

import os

def _write_temp_file(test_case, data):
	f = NamedTemporaryFile(delete=False)
	try:
		f.write(data)
	finally:
		f.close()
	test_case.addCleanup(os.remove, f.name)
	return f.name


@skipUnless(PLATFORM == 'Windows', 'SMB login is a Windows feature')
class OpenDirectoryShareTest(TestCase):
	def test_permission_error_connects_and_retries_once(self):
		from core.commands.network_shares import ShareLogin

		pane = MagicMock()
		pane.set_path.side_effect = [PermissionError(), None]
		with patch('core.commands.opening.is_dir', return_value=True), \
				patch(
					'core.commands.network_shares.log_in_to_share',
					return_value=ShareLogin.CONNECTED
				), \
				patch('core.commands.opening.show_alert') as alert:
			OpenDirectory(pane)('file:////server/share')
		self.assertEqual(2, pane.set_path.call_count)
		alert.assert_not_called()

	def test_permission_error_while_checking_share_offers_login(self):
		from core.commands.network_shares import ShareLogin
		pane = MagicMock()
		with patch(
				'core.commands.opening.is_dir',
				side_effect=[PermissionError(), True]
		), patch(
				'core.commands.network_shares.log_in_to_share',
				return_value=ShareLogin.CONNECTED
		) as login:
			OpenDirectory(pane)('file:////server/share')
		login.assert_called_once_with('file:////server/share')
		pane.set_path.assert_called_once_with('file:////server/share', onerror=None)

	def test_local_permission_error_keeps_access_denied_alert(self):
		from core.commands.network_shares import ShareLogin
		pane = MagicMock()
		with patch('core.commands.opening.is_dir', side_effect=PermissionError()), \
				patch(
					'core.commands.network_shares.log_in_to_share',
					return_value=ShareLogin.NOT_A_SHARE
				), \
				patch('core.commands.opening.show_alert') as alert:
			OpenDirectory(pane)('file:///C:/private')
		alert.assert_called_once()

class OpenOrViewTest(TestCase):
	def test_dispatches_by_cursor_target(self):
		cases = (
			# label, is_dir, is_viewable, expected command
			('directory', True, True, 'open'),
			('file', False, True, 'view_file'),
			('binary', False, False, 'open'),
			(None, False, True, 'open'),
		)
		for label, cursor_is_dir, viewable, expected_command in cases:
			with self.subTest(label=label, viewable=viewable):
				url = 'file://' + label if label else None
				pane = FakePane(url=url)
				with patch(
						'core.commands.opening.is_dir_checked',
						return_value=cursor_is_dir
				), patch(
						'core.commands.opening._is_viewable',
						return_value=viewable
				):
					OpenOrView(pane)()
				self.assertEqual([expected_command], pane.commands_run)

	def test_non_local_url_falls_back_to_open(self):
		# Scheme check happens before _is_viewable, so a viewable-looking
		# remote file still can't be handed to the (local-only) viewer.
		pane = FakePane(url='http://example.com/file.txt')
		with patch(
				'core.commands.opening.is_dir_checked', return_value=False
		), patch('core.commands.opening._is_viewable', return_value=True):
			OpenOrView(pane)()
		self.assertEqual(['open'], pane.commands_run)

	def test_unreadable_file_system_alerts_and_runs_nothing(self):
		# A share that went away: is_dir_checked(...) has alerted and answers
		# None. Stop there - delegating to `open` would only alert again.
		pane = FakePane(url='file://gone')
		with patch(
				'core.commands.opening.is_dir_checked', return_value=None
		), patch('core.commands.opening._is_viewable', return_value=True):
			OpenOrView(pane)()
		self.assertEqual([], pane.commands_run)

@skipUnless(PLATFORM == 'Windows', '.lnk shortcuts are a Windows concept')
class OpenShortcutTest(TestCase):
	def test_shortcut_to_directory_navigates_instead_of_launching(self):
		# Upper case on purpose: Windows file names are case-insensitive.
		pane, shell_execute = self._open(r'C:\a\x.LNK', target='C:\\dir')
		pane.set_path.assert_called_once_with(as_url('C:\\dir'))
		shell_execute.assert_not_called()
	def test_shortcut_without_target_is_launched(self):
		pane, shell_execute = self._open(r'C:\a\x.lnk', target='')
		pane.set_path.assert_not_called()
		shell_execute.assert_called_once()
	def _open(self, path, target):
		pane = MagicMock()
		with patch(
				'core.commands.opening.shortcut_target', return_value=target
		), patch('core.commands.opening.is_dir', return_value=True), \
				patch('win32api.ShellExecute') as shell_execute:
			_open_local_files_win([path], pane)
		return pane, shell_execute

@skipUnless(PLATFORM == 'Windows', 'ShellExecute is a Windows API')
class OpenFailureTest(TestCase):
	path = r'C:\a\x.json'

	def test_yes_opens_the_windows_open_with_dialog(self):
		import pywintypes
		error = pywintypes.error(
			31, 'ShellExecute',
			'A device attached to the system is not functioning.'
		)
		pane, shell_execute, show_alert = self._open(
			[error, None], return_value=self._yes()
		)
		self.assertIn(self.path, show_alert.call_args[0][0])
		self.assertEqual(2, shell_execute.call_count)
		self.assertEqual('openas', shell_execute.call_args.args[1])
		self.assertEqual(self.path, shell_execute.call_args.args[2])

	def test_no_does_not_open_the_windows_dialog(self):
		import pywintypes
		error = pywintypes.error(
			31, 'ShellExecute',
			'A device attached to the system is not functioning.'
		)
		_, shell_execute, show_alert = self._open([error], return_value=self._no())
		show_alert.assert_called_once()
		shell_execute.assert_called_once()

	def test_cancelled_uac_prompt_stays_silent(self):
		import pywintypes
		from winerror import ERROR_CANCELLED
		error = pywintypes.error(
			ERROR_CANCELLED, 'ShellExecute',
			'The operation was canceled by the user.'
		)
		_, shell_execute, show_alert = self._open([error])
		show_alert.assert_not_called()
		shell_execute.assert_called_once()

	def test_open_with_failure_shows_a_fallback_alert(self):
		import pywintypes
		error = pywintypes.error(
			31, 'ShellExecute',
			'A device attached to the system is not functioning.'
		)
		_, shell_execute, show_alert = self._open(
			[error, error], return_value=self._yes()
		)
		self.assertEqual(2, show_alert.call_count)
		self.assertEqual(2, shell_execute.call_count)

	def _open(self, side_effect, return_value=None):
		pane = MagicMock()
		with patch('win32api.ShellExecute', side_effect=side_effect) as shell_execute:
			with patch(
				'core.commands.opening.show_alert', return_value=return_value
			) as show_alert, patch(
				'core.commands.opening.is_shortcut', return_value=False
			):
				_open_local_files_win([self.path], pane)
		return pane, shell_execute, show_alert

	@staticmethod
	def _yes():
		from fman import YES
		return YES

	@staticmethod
	def _no():
		from fman import NO
		return NO

class _ViewerTestCase(TestCase):

	# Every test here needs the same three seams: what the file system says
	# the URL is, which viewer claims it, and whether an alert was shown.
	def setUp(self):
		super().setUp()
		self.viewer = MagicMock()
		self.is_dir = self._patch('is_dir_checked', return_value=False)
		self.viewer_for = self._patch('viewer_for', return_value=self.viewer)
		self.show_alert = self._patch('show_alert')
	def _patch(self, name, **kwargs):
		patcher = patch('core.commands.opening.' + name, **kwargs)
		self.addCleanup(patcher.stop)
		return patcher.start()

# Which viewer claims which file now lives in the registry, and is covered by
# core/tests/test_viewers.py. These tests are about the commands' own job:
# validate, pick the target pane, decide focus, alert when nothing handles it.
class ViewFileTest(_ViewerTestCase):
	def test_viewable_file_opens_its_viewer(self):
		path = _write_temp_file(self, b'hello world')
		ViewFile(FakePane(url=as_url(path)))()
		self.viewer.show.assert_called_once()
		self.show_alert.assert_not_called()

	def test_file_no_viewer_handles_shows_an_alert(self):
		path = _write_temp_file(self, b'MZ\x00\x00binary stuff')
		self.viewer_for.return_value = None
		ViewFile(FakePane(url=as_url(path)))()
		self.show_alert.assert_called_once()

class ViewFileInOtherPaneTest(_ViewerTestCase):
	def test_mounts_in_other_pane_without_stealing_focus(self):
		path = _write_temp_file(self, b'hello world')
		source, target = self._panes(as_url(path), None)
		ViewFileInOtherPane(source)()
		# Mounted into the OTHER pane, and told not to grab keyboard focus so
		# browsing stays in the source pane.
		self.assertIs(target, self.viewer.show.call_args[0][0])
		self.assertFalse(self.viewer.show.call_args.kwargs['focus_view'])
		self.show_alert.assert_not_called()

	def test_single_pane_views_in_place_and_takes_focus(self):
		path = _write_temp_file(self, b'hello world')
		only, = self._panes(as_url(path))
		ViewFileInOtherPane(only)()
		self.assertIs(only, self.viewer.show.call_args[0][0])
		self.assertTrue(self.viewer.show.call_args.kwargs['focus_view'])
		self.show_alert.assert_not_called()

	def test_validation_failure_mounts_nothing(self):
		source, target = self._panes(None, None)  # no file selected
		ViewFileInOtherPane(source)()
		self.show_alert.assert_called_once()
		self.viewer.show.assert_not_called()

	def _panes(self, *urls):
		window = FakeWindow()
		window._panes = [FakePane(window, url) for url in urls]
		return window._panes
