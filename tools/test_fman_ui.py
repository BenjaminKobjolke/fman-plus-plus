import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest import main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import fman_ui


class FmanUiTest(TestCase):
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
				if os.name == 'nt':
					fman_ui.subprocess.run.assert_any_call(
						['attrib', '+h', str(Path(session['left']) / 'hidden.txt')],
						check=True, stdout=fman_ui.subprocess.DEVNULL,
						stderr=fman_ui.subprocess.DEVNULL)
				self.assertEqual(session, fman_ui._read_current())

	def test_bare_file_name_is_resolved_against_selected_pane(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'fman-ui'
			session = {'session_id': 'x', 'pid': 1, 'port': 1,
				'token_path': str(root / 'profile' / 'token'),
				'profile': str(Path(temp) / 'profile'),
				'left': 'L', 'right': 'R'}
			Path(session['token_path']).parent.mkdir(parents=True)
			Path(session['token_path']).write_text('token')
			root.mkdir(exist_ok=True)
			(root / 'current.json').write_text(json.dumps(session))
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
