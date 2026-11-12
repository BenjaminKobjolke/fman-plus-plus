"""Tests for restarting the isolated fman UI session."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import fman_ui
import restart
import session_reaper


class FmanUiRestartTest(TestCase):
	def _session(self, root):
		profile = root / 'profile'
		local = profile / 'Local'
		local.mkdir(parents=True)
		settings = local / 'Settings.json'
		settings.write_text('{"kept": true}', encoding='utf-8')
		session = {
			'session_id': 'test', 'pid': 10, 'start_time': 1.0,
			'fman_pid': 11, 'fman_start_time': 2.0, 'profile': str(profile),
			'left': str(root / 'left'), 'right': str(root / 'right'), 'port': 123,
			'token_path': str(local / 'token'),
		}
		(root / session_reaper.SESSION_FILE).write_text(json.dumps(session))
		return session, settings

	def test_restart_keeps_profile_and_restarts_with_same_arguments(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			root.mkdir()
			session, settings = self._session(root)
			current = Path(temp) / 'current.json'
			def start_again(updated_session, _session_root):
				updated_session.update(pid=21, start_time=3.0,
					fman_pid=22, fman_start_time=4.0)
				return {'ok': True}
			with patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_current_path', return_value=current), \
				patch.object(fman_ui, '_api', side_effect=URLError('exiting')) as api, \
				patch.object(restart, '_wait_for_exit'), \
				patch.object(fman_ui, '_start_fman', side_effect=start_again) as start:
				self.assertEqual(
					{'ok': True}, fman_ui._run(SimpleNamespace(action='restart')))
			api.assert_called_once_with(session, 'POST', '/v1/command', {
				'name': 'quit', 'args': {}, 'pane': 0})
			self.assertEqual(str(root / 'profile'), start.call_args.args[0]['profile'])
			self.assertEqual(
				[session['left'], session['right']],
				[start.call_args.args[0]['left'], start.call_args.args[0]['right']])
			self.assertEqual('{"kept": true}', settings.read_text(encoding='utf-8'))
			self.assertTrue(root.exists())
			self.assertFalse((root / restart.RESTART_MARKER).exists())
			self.assertEqual(session, json.loads(current.read_text(encoding='utf-8')))
			self.assertEqual((
					21, 3.0, 22, 4.0), (
				json.loads(current.read_text(encoding='utf-8'))['pid'],
				json.loads(current.read_text(encoding='utf-8'))['start_time'],
				json.loads(current.read_text(encoding='utf-8'))['fman_pid'],
				json.loads(current.read_text(encoding='utf-8'))['fman_start_time']))

	def test_restart_ignores_expected_quit_request_failures(self):
		for error in (URLError('closed'), RuntimeError('closed'), OSError('closed'),
				TimeoutError('closed')):
			with self.subTest(error=type(error).__name__), TemporaryDirectory() as temp:
				root = Path(temp) / 'session'
				root.mkdir()
				session, _ = self._session(root)
				with patch.object(fman_ui, '_read_current', return_value=session), \
					patch.object(fman_ui, '_api', side_effect=error), \
					patch.object(restart, '_wait_for_exit'), \
					patch.object(fman_ui, '_start_fman', return_value={'ok': True}):
					self.assertEqual({'ok': True},
						fman_ui._run(SimpleNamespace(action='restart')))
				self.assertFalse((root / restart.RESTART_MARKER).exists())

	def test_restart_clears_marker_if_new_start_fails_without_deleting_session(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			root.mkdir()
			session, _ = self._session(root)
			with patch.object(fman_ui, '_read_current', return_value=session), \
				patch.object(fman_ui, '_api', side_effect=OSError('exiting')), \
				patch.object(restart, '_wait_for_exit'), \
				patch.object(
					fman_ui, '_start_fman', side_effect=RuntimeError('failed')):
				with self.assertRaisesRegex(RuntimeError, 'failed'):
					fman_ui._run(SimpleNamespace(action='restart'))
			self.assertTrue(root.exists())
			self.assertFalse((root / restart.RESTART_MARKER).exists())

	def test_start_fman_updates_current_and_session_identity(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			root.mkdir()
			session, _ = self._session(root)
			session['fman_pid'] = 99
			session['fman_start_time'] = 100
			with patch.object(fman_ui.subprocess, 'Popen') as popen, \
				patch.object(fman_ui, 'process_start_time', return_value=3.0), \
				patch.object(
					fman_ui, 'fman_process_identity', return_value=(22, 4.0)), \
				patch.object(fman_ui, '_wait_for_state', return_value={'ok': True}):
				popen.return_value.pid = 21
				fman_ui._start_fman(session, root)
				written = json.loads((root / session_reaper.SESSION_FILE).read_text())
				self.assertEqual(
					(21, 3.0, 22, 4.0), (written['pid'], written['start_time'],
					written['fman_pid'], written['fman_start_time']))
				self.assertEqual(
					[session['left'], session['right']], popen.call_args.args[0][-2:])

	def test_restart_kills_recorded_process_after_timeout(self):
		session = {'pid': 10, 'start_time': 1, 'fman_pid': 11, 'fman_start_time': 2}
		with patch.object(restart.time, 'monotonic', side_effect=[0, 16]), \
			patch.object(restart.time, 'sleep'), \
			patch.object(restart, '_process_is_running', return_value=True), \
			patch.object(restart, 'kill_process') as kill:
			restart._wait_for_exit(session)
		kill.assert_called_once_with(11, 2)


if __name__ == '__main__':
	from unittest import main
	main()
