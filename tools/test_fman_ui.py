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
				patch.object(fman_ui, 'cleanup_recycle_bin', return_value=2), \
				patch.object(fman_ui.subprocess, 'run'):
				result = fman_ui._run(SimpleNamespace(action='close'))
		self.assertEqual(
			{'ok': True, 'recycle_bin_entries_removed': 2}, result)
		self.assertFalse(session_root.exists())

	def test_close_cleans_session_even_when_recycle_cleanup_fails(self):
		with TemporaryDirectory() as temp:
			session_root = Path(temp) / 'session'
			profile = session_root / 'profile'
			profile.mkdir(parents=True)
			current_path = Path(temp) / 'current.json'
			current_path.write_text('{}', encoding='utf-8')
			session = {'profile': str(profile), 'pid': 123}
			with patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_current_path', return_value=current_path), \
				patch.object(fman_ui, 'cleanup_recycle_bin',
					side_effect=OSError('Recycle Bin unavailable')), \
				patch.object(fman_ui.subprocess, 'run'):
				result = fman_ui._run(SimpleNamespace(action='close'))
		self.assertEqual(
			{'ok': True, 'recycle_bin_entries_removed': 0}, result)
		self.assertFalse(session_root.exists())
		self.assertFalse(current_path.exists())

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

	def test_launch_creates_isolated_profile_and_fixture_layout(self):
		with TemporaryDirectory() as temp:
			with patch.dict(os.environ, {'TEMP': temp}), \
				patch.object(fman_ui, '_reserve_port', return_value=45678), \
				patch.object(fman_ui, '_wait_for_state'), \
				patch.object(fman_ui.subprocess, 'Popen') as popen, \
				patch.object(fman_ui.subprocess, 'run'):
				popen.return_value.pid = 123
				args = SimpleNamespace(left=None, right=None)
				session = fman_ui._launch(args)
				settings = json.loads(
					(Path(session['profile']) / 'Local' / 'Settings.json').read_text())
				self.assertTrue(settings['scripting_api']['automation'])
				self.assertEqual(45678, settings['scripting_api']['port'])
				session_settings = json.loads(
					(Path(session['profile']) / 'Local' / 'Session.json').read_text())
				self.assertEqual([{}, {}], session_settings['panes'])
				self.assertTrue((Path(session['left']) / 'visible.txt').exists())
				self.assertTrue((Path(session['left']) / 'hidden.txt').exists())
				self.assertTrue((Path(session['left']) / 'folder').is_dir())
				self.assertTrue((Path(session['left']) / '[--brackets--]' /
					'visible.txt').exists())
				if os.name == 'nt':
					fman_ui.subprocess.run.assert_any_call(
						['attrib', '+h', str(Path(session['left']) / 'hidden.txt')],
						check=True, stdout=fman_ui.subprocess.DEVNULL,
						stderr=fman_ui.subprocess.DEVNULL)
				self.assertEqual(session, fman_ui._read_current())

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
				poll=lambda: None,
				kill=lambda: setattr(process, 'killed', True),
			)
			process.killed = False
			with patch.object(fman_ui.time, 'monotonic', side_effect=[0, 61]), \
				patch.object(fman_ui.time, 'sleep'), \
				patch.object(fman_ui, '_api', side_effect=OSError('not ready')):
				with self.assertRaisesRegex(RuntimeError, 'last log line'):
					fman_ui._wait_for_state({}, process, log)
			self.assertTrue(process.killed)


if __name__ == '__main__':
	main()
