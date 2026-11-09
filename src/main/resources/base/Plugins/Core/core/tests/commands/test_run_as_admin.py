from core.tests.commands import FakePane
from fman import PLATFORM
from fman.url import as_url
from contextlib import contextmanager, ExitStack
from unittest import TestCase, skipUnless
from unittest.mock import MagicMock, patch


class Pane(FakePane):
	def get_path(self):
		return 'file:///'


@skipUnless(PLATFORM == 'Windows', 'ShellExecute is a Windows API')
class RunAsAdministratorTest(TestCase):
	def setUp(self):
		from core.commands.run_as_admin import RunAsAdministrator
		self.pane = MagicMock(spec=Pane)
		self.pane.get_path.return_value = 'file:///'
		self.pane.get_file_under_cursor.return_value = as_url(r'C:\tools\app.exe')
		self.command = RunAsAdministrator(self.pane)

	def test_runs_one_chosen_file_with_runas_verb(self):
		with self._run([as_url(r'C:\tools\app.exe')]) as shell_execute:
			shell_execute.assert_called_once_with(
				0, 'runas', r'C:\tools\app.exe', None, r'C:\tools', 1
			)

	def test_runs_each_chosen_file(self):
		with self._run([
			as_url(r'C:\tools\one.exe'), as_url(r'C:\tools\two.exe')
		]) as shell_execute:
			self.assertEqual(2, shell_execute.call_count)
			self.assertEqual('runas', shell_execute.call_args_list[0].args[1])
			self.assertEqual('runas', shell_execute.call_args_list[1].args[1])

	def test_cancelled_uac_prompt_stays_silent(self):
		import pywintypes
		from winerror import ERROR_CANCELLED
		error = pywintypes.error(
			ERROR_CANCELLED, 'ShellExecute',
			'The operation was canceled by the user.'
		)
		with self._run(
			[as_url(r'C:\tools\app.exe')], side_effect=error
		) as shell_execute:
			self.assertEqual(1, shell_execute.call_count)
			self.alert.assert_not_called()

	def test_other_shell_execute_error_shows_path_and_windows_message(self):
		import pywintypes
		error = pywintypes.error(31, 'ShellExecute', 'Windows error message')
		with self._run([as_url(r'C:\tools\app.exe')], side_effect=error):
			self.alert.assert_called_once()
			message = self.alert.call_args.args[0]
			self.assertIn(r'C:\tools\app.exe', message)
			self.assertIn('Windows error message', message)

	def test_folder_shows_alert_without_shell_execute(self):
		with self._run([as_url(r'C:\tools\folder')], is_dir=True) as shell_execute:
			shell_execute.assert_not_called()
			self.alert.assert_called_once()
			self.assertIn('folder', self.alert.call_args.args[0])

	def test_no_chosen_files_shows_no_selection_alert(self):
		with self._run([]) as shell_execute:
			shell_execute.assert_not_called()
			self.alert.assert_called_once()

	@contextmanager
	def _run(self, urls, side_effect=None, is_dir=False):
		with ExitStack() as stack:
			stack.enter_context(patch.object(
				self.command, 'get_chosen_files', return_value=urls
			))
			stack.enter_context(patch(
				'core.commands.run_as_admin.resolve', side_effect=lambda url: url
			))
			stack.enter_context(patch(
				'core.commands.run_as_admin.is_dir_checked', return_value=is_dir
			))
			self.alert = stack.enter_context(patch(
				'core.commands.run_as_admin.show_alert'
			))
			shell_execute = stack.enter_context(patch(
				'win32api.ShellExecute', side_effect=side_effect
			))
			self.command()
			yield shell_execute


class RunAsAdministratorVisibilityTest(TestCase):
	def test_is_not_visible_off_windows(self):
		from core.commands.run_as_admin import RunAsAdministrator
		pane = MagicMock(spec=Pane)
		pane.get_path.return_value = 'file:///'
		pane.get_file_under_cursor.return_value = as_url(r'C:\tools\app.exe')
		command = RunAsAdministrator(pane)
		with patch('core.commands.run_as_admin.PLATFORM', 'Linux'):
			self.assertFalse(command.is_visible())

	def test_is_not_visible_for_non_file_pane(self):
		from core.commands.run_as_admin import RunAsAdministrator
		pane = MagicMock(spec=Pane)
		pane.get_path.return_value = 'ftp://example.com/'
		pane.get_file_under_cursor.return_value = 'ftp://example.com/app.exe'
		command = RunAsAdministrator(pane)
		with patch('core.commands.run_as_admin.PLATFORM', 'Windows'):
			self.assertFalse(command.is_visible())
