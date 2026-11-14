"""Tests for launch setup and arguments in the fman UI driver."""

import json
import os
from pathlib import Path
import sys
import tempfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import fman_ui
from parser import parser


class FmanUiLaunchTest(TestCase):
	def test_root_uses_system_temp_directory_when_temp_is_unset(self):
		with patch.dict(os.environ), \
			patch.object(tempfile, 'gettempdir', return_value='system-temp'):
			os.environ.pop('TEMP', None)
			self.assertEqual(Path('system-temp') / 'fman-ui', fman_ui._root())

	def _launch(self, temp, *, large=0, deep=0, core_settings=None, left=None):
		patches = (
			patch.dict(os.environ, {'TEMP': temp}),
			patch.object(fman_ui, '_reserve_port', return_value=45678),
			patch.object(fman_ui, '_root', return_value=Path(temp) / 'fman-ui'),
			patch.object(fman_ui, '_wait_for_state'),
			patch.object(fman_ui, 'process_start_time', return_value=10.5),
			patch.object(fman_ui, 'fman_process_identity',
				return_value=(456, 20)),
			patch.object(fman_ui, 'reap_stale'),
			patch.object(fman_ui.subprocess, 'Popen'),
			patch.object(fman_ui.subprocess, 'run'),
		)
		with patches[0], patches[1], patches[2], patches[3], patches[4], \
			patches[5], patches[6], patches[7] as popen, patches[8]:
			popen.return_value.pid = 123
			session = fman_ui._launch(SimpleNamespace(
				left=left, right=None, large=large, deep=deep,
				core_settings=core_settings))
			self.popen_calls = popen.call_args_list
			return session

	def test_launch_creates_isolated_profile_and_fixture_layout(self):
		with TemporaryDirectory() as temp, patch.dict(os.environ, {'TEMP': temp}):
			with patch.object(fman_ui, '_reserve_port', return_value=45678), \
				patch.object(fman_ui, '_wait_for_state'), \
				patch.object(fman_ui, 'process_start_time', return_value=10.5), \
				patch.object(fman_ui, 'fman_process_identity',
					return_value=(456, 20)), \
				patch.object(fman_ui, 'reap_stale') as reap_stale, \
				patch.object(fman_ui.subprocess, 'Popen') as popen, \
				patch.object(fman_ui.subprocess, 'run'):
				popen.return_value.pid = 123
				session = fman_ui._launch(SimpleNamespace(
					left=None, right=None, large=0, deep=0, core_settings=None))
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
				self.assertTrue((Path(session['left']) / 'ages' /
					'age_400d_old.txt').exists())
				video = Path(session['left']) / 'video.mp4'
				self.assertEqual(
					(Path(fman_ui.__file__).resolve().parents[2] /
						'examples' / 'left_pane' / 'dummy.mp4').stat().st_size,
					video.stat().st_size)
				self.assertFalse((Path(session['right']) / 'video.mp4').exists())
				self.assertEqual('1.9.0', session['build']['version'])
				self.assertIn('commit', session['build'])
				self.assertIn('dirty', session['build'])
				self.assertIn('checkout_path', session['build'])
				self.assertIn('python', session['build'])
				if os.name == 'nt':
					fman_ui.subprocess.run.assert_any_call(
						['attrib', '+h', str(Path(session['left']) / 'hidden.txt')],
						check=True, stdout=fman_ui.subprocess.DEVNULL,
						stderr=fman_ui.subprocess.DEVNULL)
				self.assertEqual(session, fman_ui._read_current())
				reap_stale.assert_called_once()
				session_data = json.loads((Path(session['profile']).parent /
					'session.json').read_text())
				self.assertEqual(session['build'], session_data['build'])
				self.assertEqual(123, session_data['pid'])
				self.assertEqual(10.5, session_data['start_time'])
				self.assertEqual(456, session_data['fman_pid'])
				self.assertEqual(20, session_data['fman_start_time'])
				self.assertIn(
					'session_reaper.py', popen.call_args_list[1].args[0][1])

	def test_launch_creates_large_left_fixture_and_core_settings(self):
		with TemporaryDirectory() as temp:
			session = self._launch(
				temp, large=3, core_settings='{"file_age_style": "tint"}')
			self.assertEqual(3, len(list((Path(session['left']) / 'large').iterdir())))
			self.assertFalse((Path(session['right']) / 'large').exists())
			settings_path = (Path(session['profile']) / 'Plugins' / 'User' /
				'Settings' / 'Core Settings.json')
			self.assertEqual({'file_age_style': 'tint'},
				json.loads(settings_path.read_text(encoding='utf-8')))

	def test_launch_creates_deep_left_fixture_and_reports_level_six(self):
		with TemporaryDirectory() as temp:
			session = self._launch(temp, deep=2)
			deep = Path(session['left']) / 'deep' / 'level_1' / 'level_2' / \
				'level_3' / 'level_4' / 'level_5' / 'level_6'
			self.assertEqual(str(deep), session['deep'])
			self.assertTrue(deep.is_dir())

	def test_launch_with_caller_left_does_not_create_deep_fixture(self):
		with TemporaryDirectory() as temp:
			left = Path(temp) / 'provided-left'
			left.mkdir()
			session = self._launch(temp, deep=2, left=str(left))
			self.assertNotIn('deep', session)
			self.assertFalse((left / 'deep').exists())

	def test_launch_starts_children_in_new_sessions_only_on_posix(self):
		for name, expected in (('posix', True), ('nt', False)):
			with self.subTest(os_name=name), TemporaryDirectory() as temp:
				with patch.object(fman_ui, 'os', SimpleNamespace(
					name=name, environ=os.environ)):
					self._launch(temp)
				self.assertEqual(2, len(self.popen_calls))
				self.assertEqual(
					[expected, expected],
					[call.kwargs['start_new_session'] for call in self.popen_calls])

	def test_invalid_launch_options_fail_before_session_directory_is_created(self):
		with TemporaryDirectory() as temp, patch.dict(os.environ, {'TEMP': temp}):
			for args in (
				SimpleNamespace(left=None, right=None, large=-1, deep=0,
					core_settings=None),
				SimpleNamespace(left=None, right=None, large=0, deep=0,
					core_settings='[1]'),
				SimpleNamespace(left=None, right=None, large=0, deep=-1,
					core_settings=None),
				SimpleNamespace(left=None, right=None, large=0, deep=5001,
					core_settings=None),
			):
				with self.subTest(args=args), self.assertRaises(ValueError):
					fman_ui._launch(args)
				self.assertFalse((Path(temp) / 'fman-ui').exists())

	def test_parser_accepts_large_and_core_settings(self):
		args = parser().parse_args([
			'launch', '--large', '5000', '--core-settings', '{}'])
		self.assertEqual(5000, args.large)
		self.assertEqual('{}', args.core_settings)

	def test_parser_accepts_deep(self):
		args = parser().parse_args(['launch', '--deep', '10'])
		self.assertEqual(10, args.deep)

