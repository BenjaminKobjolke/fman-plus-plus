import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest import main
from unittest.mock import Mock, patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import recycle_cleanup
import fman_ui
import session_reaper
import test_fman_ui_session_reaper
import test_fman_ui_fixtures
import test_fman_ui_launch
import test_fman_ui_restart
import test_fman_ui_build_info


class FmanUiTest(TestCase):
	def _write_session(self, temp):
		root = Path(temp) / 'fman-ui'
		session = {'session_id': 'x', 'pid': 1, 'port': 1,
			'token_path': str(root / 'profile' / 'token'),
			'profile': str(Path(temp) / 'profile'),
			'left': 'L', 'right': 'R'}
		Path(session['token_path']).parent.mkdir(parents=True)
		Path(session['token_path']).write_text('token')
		root.mkdir(exist_ok=True)
		(root / 'current.json').write_text(json.dumps(session))

	def test_close_reports_the_number_of_removed_recycle_bin_entries(self):
		with TemporaryDirectory() as temp:
			session_root = Path(temp) / 'session'
			profile = session_root / 'profile'
			profile.mkdir(parents=True)
			current_path = Path(temp) / 'current.json'
			current_path.write_text('{}', encoding='utf-8')
			session = {'profile': str(profile), 'pid': 123}
			with patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_current_path', return_value=current_path), \
				patch.object(fman_ui, 'close_session', return_value=2) as close_session:
				result = fman_ui._run(SimpleNamespace(action='close'))
			close_session.assert_called_once_with(session_root)
		self.assertEqual(
			{'ok': True, 'recycle_bin_entries_removed': 2}, result)
		self.assertFalse(session_root.exists())
		self.assertFalse(current_path.exists())

	def test_close_cleans_session_even_when_recycle_cleanup_fails(self):
		self._assert_close_cleans_files(removed_entries=0)

	def _assert_close_cleans_files(self, removed_entries):
		with TemporaryDirectory() as temp:
			session_root = Path(temp) / 'session'
			profile = session_root / 'profile'
			profile.mkdir(parents=True)
			current_path = Path(temp) / 'current.json'
			current_path.write_text('{}', encoding='utf-8')
			session = {'profile': str(profile), 'pid': 123}
			with patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_current_path', return_value=current_path), \
				patch.object(fman_ui, 'close_session',
					return_value=removed_entries):
				result = fman_ui._run(SimpleNamespace(action='close'))
		self.assertEqual({
			'ok': True,
			'recycle_bin_entries_removed': removed_entries,
		}, result)
		self.assertFalse(session_root.exists())
		self.assertFalse(current_path.exists())

	def test_close_old_format_session_falls_back_to_taskkill(self):
		with TemporaryDirectory() as temp:
			current_path = Path(temp) / 'current.json'
			current_path.write_text('{}', encoding='utf-8')
			session = {'profile': str(Path(temp) / 'session' / 'profile'), 'pid': 123}
			with patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_current_path', return_value=current_path), \
				patch.object(fman_ui, 'close_session') as close_session, \
				patch.object(fman_ui.subprocess, 'run') as run:
				fman_ui._run(SimpleNamespace(action='close'))
			close_session.assert_called_once_with(Path(session['profile']).parent)
			run.assert_called_once_with(
				['taskkill', '/PID', '123', '/T', '/F'], check=False,
				stdout=fman_ui.subprocess.DEVNULL,
				stderr=fman_ui.subprocess.DEVNULL)
			self.assertFalse(current_path.exists())

	def test_driver_command_touches_session_file_before_api_call(self):
		with TemporaryDirectory() as temp:
			profile = Path(temp) / 'profile'
			profile.mkdir()
			session_root = profile.parent
			session_file = session_root / session_reaper.SESSION_FILE
			session_file.write_text('{}')
			session = {'profile': str(profile)}
			args = SimpleNamespace(action='state')
			with patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_api', return_value={'ok': True}) as api, \
				patch.object(fman_ui.os, 'utime') as utime:
				self.assertEqual({'ok': True}, fman_ui._run(args))
			utime.assert_called_once_with(session_file, None)
			api.assert_called_once()

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

	def test_command_timeout_reports_an_open_dialog(self):
		dialog = {
			'type': 'MessageBox', 'title': 'Confirm', 'text': 'Continue?',
			'buttons': ['&Yes', '&No'],
		}
		args = SimpleNamespace(
			action='command', name='move_to_trash', args_json='{}',
			pane=0, settle=500,
		)
		with patch.object(fman_ui, '_read_current', return_value={}), \
			patch.object(fman_ui, '_api', side_effect=[
				URLError(TimeoutError('timed out')), {'dialog': dialog},
			]) as api:
			self.assertEqual(
				{'running': True, 'dialog': dialog}, fman_ui._run(args))
		self.assertEqual('/v1/dialog', api.call_args.args[2])

	def test_command_timeout_without_a_dialog_keeps_the_timeout_error(self):
		args = SimpleNamespace(
			action='command', name='move_to_trash', args_json='{}',
			pane=0, settle=500,
		)
		with patch.object(fman_ui, '_read_current', return_value={}), \
			patch.object(fman_ui, '_api', side_effect=[
				TimeoutError('timed out'), {'dialog': None},
			]):
			with self.assertRaisesRegex(TimeoutError, 'timed out'):
				fman_ui._run(args)

	def test_dialog_subcommand_reads_the_active_dialog(self):
		args = fman_ui._parser().parse_args(['dialog'])
		with patch.object(fman_ui, '_read_current', return_value={}), \
			patch.object(fman_ui, '_api', return_value={'dialog': None}) as api:
			self.assertEqual({'dialog': None}, fman_ui._run(args))
		api.assert_called_once_with({}, 'GET', '/v1/dialog')

	def test_viewer_subcommand_reads_the_selected_pane(self):
		args = fman_ui._parser().parse_args(['viewer', '--pane', '1'])
		with patch.object(fman_ui, '_read_current', return_value={}), \
			patch.object(fman_ui, '_api', return_value={'viewer': None}) as api:
			self.assertEqual({'viewer': None}, fman_ui._run(args))
		api.assert_called_once_with({}, 'GET', '/v1/viewer?pane=1')

	def test_bare_file_name_is_resolved_against_selected_pane(self):
		with TemporaryDirectory() as temp:
			self._write_session(temp)
			with patch.dict(os.environ, {'TEMP': temp}), \
				patch.object(fman_ui, '_api', side_effect=[
					{'panes': [{'path': 'file:///C:/fixture'}]}, {'ok': True},
				]) as api:
				self.assertEqual(0, fman_ui.main([
					'click', '--file', 'visible.txt', '--settle', '0']))
				self.assertEqual(
					'file:///C:/fixture/visible.txt',
					api.call_args_list[1].args[3]['file'],
				)

	def test_drag_posts_start_and_end_coordinates(self):
		with TemporaryDirectory() as temp:
			self._write_session(temp)
			with patch.dict(os.environ, {'TEMP': temp}), \
				patch.object(fman_ui, '_api', return_value={'ok': True}) as api:
				self.assertEqual(0, fman_ui.main([
					'drag', '--x', '1', '--y', '2', '--to-x', '3', '--to-y', '4',
					'--settle', '0',
				]))
		self.assertEqual(
			('POST', '/v1/drag', {'x': 1, 'y': 2, 'to_x': 3, 'to_y': 4}),
			api.call_args.args[1:],
		)

	def test_bracketed_and_spaced_file_names_remain_unencoded(self):
		with TemporaryDirectory() as temp:
			self._write_session(temp)
			for name in ('[--brackets--]/visible.txt', 'file name.txt'):
				with self.subTest(name=name), \
					patch.dict(os.environ, {'TEMP': temp}), \
					patch.object(fman_ui, '_api', side_effect=[
						{'panes': [{'path': 'file:///C:/fixture'}]}, {'ok': True},
					]) as api:
					self.assertEqual(0, fman_ui.main([
						'click', '--file', name, '--settle', '0']))
				self.assertEqual(
					'file:///C:/fixture/' + name,
					api.call_args_list[1].args[3]['file'],
					)

	def test_launch_wait_timeout_kills_process_and_includes_log_tail(self):
		with TemporaryDirectory() as temp:
			log = Path(temp) / 'fman.log'
			log.write_text('last log line\n')
			process = SimpleNamespace(
				pid=123,
				poll=lambda: None,
			)
			with patch.object(fman_ui.time, 'monotonic', side_effect=[0, 61]), \
				patch.object(fman_ui.time, 'sleep'), \
				patch.object(fman_ui, '_api', side_effect=OSError('not ready')), \
				patch.object(fman_ui, 'kill_process') as kill_process:
				with self.assertRaisesRegex(RuntimeError, 'last log line'):
					fman_ui._wait_for_state({'start_time': 10}, process, log)
			kill_process.assert_called_once_with(process.pid, 10)



def load_tests(loader, tests, pattern):
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_session_reaper.SessionReaperTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_fixtures.FixturesTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_launch.FmanUiLaunchTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_restart.FmanUiRestartTest))
	tests.addTests(loader.loadTestsFromTestCase(
		test_fman_ui_build_info.BuildInfoTest))
	return tests


if __name__ == '__main__':
	main()
