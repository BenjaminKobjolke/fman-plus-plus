"""Tests for launch setup and arguments in the fman UI driver."""

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import fman_ui


class FmanUiLaunchTest(TestCase):
	def test_launch_creates_archive_fixture_and_reports_its_path(self):
		with TemporaryDirectory() as temp:
			session = self._launch(temp, archive=3)
			archive = Path(session['left']) / 'archive.zip'
			self.assertEqual(str(archive), session['archive'])
			self.assertTrue(archive.is_file())

	def test_launch_with_caller_left_does_not_create_archive_fixture(self):
		with TemporaryDirectory() as temp:
			left = Path(temp) / 'provided-left'
			left.mkdir()
			session = self._launch(temp, archive=3, left=str(left))
			self.assertNotIn('archive', session)
			self.assertFalse((left / 'archive.zip').exists())

	def _launch(self, temp, *, large=0, deep=0, archive=0,
			core_settings=None, left=None,
			previous_version=None, first_start=False, demo=None,
		network_share=False):
		patches = (
			patch.dict(os.environ, {'TEMP': temp}),
			patch.object(fman_ui, '_reserve_port', return_value=45678),
			patch.object(fman_ui, '_root', return_value=Path(temp) / 'fman-ui'),
			patch.object(fman_ui, '_wait_for_state', return_value={'ok': True}),
			patch.object(fman_ui, 'process_start_time', return_value=10.5),
			patch.object(fman_ui, 'fman_process_identity',
				return_value=(456, 20)),
			patch.object(fman_ui, 'reap_stale'),
			patch.object(fman_ui.subprocess, 'Popen'),
			patch.object(fman_ui.subprocess, 'run'),
			patch.object(fman_ui, '_api', return_value={
				'width': 1280, 'height': 800,
				'available_width': 1920, 'available_height': 1080,
			}),
			patch.object(fman_ui, 'read_startup_prompts', return_value={
				'demo_mode': False, 'update_check_scheduled': True,
				'dialog': None,
			}),
		)
		with patches[0], patches[1], patches[2], patches[3], patches[4], \
			patches[5], patches[6], patches[7] as popen, patches[8], \
			patches[9] as api, patches[10]:
			popen.return_value.pid = 123
			session = fman_ui._launch(SimpleNamespace(
				left=left, right=None, large=large, deep=deep, archive=archive,
				core_settings=core_settings,
				previous_version=previous_version, first_start=first_start,
				demo=demo, network_share=network_share))
			self.popen_calls = popen.call_args_list
			self.api_calls = api.call_args_list
			return session

	def test_launch_creates_isolated_profile_and_fixture_layout(self):
		with TemporaryDirectory() as temp, patch.dict(os.environ, {'TEMP': temp}):
			with patch.object(fman_ui, '_reserve_port', return_value=45678), \
				patch.object(fman_ui, '_wait_for_state', return_value={'ok': True}), \
				patch.object(fman_ui, 'process_start_time', return_value=10.5), \
				patch.object(fman_ui, 'fman_process_identity',
					return_value=(456, 20)), \
				patch.object(fman_ui, 'reap_stale') as reap_stale, \
				patch.object(fman_ui.subprocess, 'Popen') as popen, \
				patch.object(fman_ui.subprocess, 'run'), \
				patch.object(fman_ui, '_api', return_value={
					'width': 1280, 'height': 800,
					'available_width': 1920, 'available_height': 1080,
				}) as api, \
				patch.object(fman_ui, 'read_startup_prompts', return_value={
					'demo_mode': False, 'update_check_scheduled': True,
					'dialog': None,
				}):
				popen.return_value.pid = 123
				session = fman_ui._launch(SimpleNamespace(
					left=None, right=None, large=0, deep=0, archive=0,
					core_settings=None,
					previous_version=None))
				settings = json.loads(
					(Path(session['profile']) / 'Local' / 'Settings.json').read_text())
				self.assertFalse(settings['error_reports'])
				self.assertFalse(settings['usage_metrics'])
				self.assertTrue(settings['scripting_api']['automation'])
				self.assertEqual(45678, settings['scripting_api']['port'])
				self.assertEqual(
					{'width': 1280, 'height': 800},
					{key: session['window'][key] for key in ('width', 'height')})
				session_settings = json.loads(
					(Path(session['profile']) / 'Local' / 'Session.json').read_text())
				self.assertEqual([{}, {}], session_settings['panes'])
				self.assertNotIn('fman_version', session_settings)
				self.assertNotIn('network_share', session)
				self.assertNotIn('network_share_unc', session)
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
				version_path = (Path(fman_ui.__file__).resolve().parents[2] /
					'src' / 'build' / 'settings' / 'base.json')
				build_settings = json.loads(
					version_path.read_text(encoding='utf-8'))
				self.assertEqual(
					build_settings['version'], session['build']['version'])
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
				self.assertEqual([
					call(session, 'POST', '/v1/window', {
						'width': 1280, 'height': 800,
					})], api.call_args_list)
				self.assertEqual(10.5, session_data['start_time'])
				self.assertEqual(456, session_data['fman_pid'])
				self.assertEqual(20, session_data['fman_start_time'])
				self.assertIn(
					'session_reaper.py', popen.call_args_list[1].args[0][1])

	def test_first_start_leaves_consent_unanswered_and_session_unseeded(self):
		with TemporaryDirectory() as temp:
			session = self._launch(temp, first_start=True)
			local = Path(session['profile']) / 'Local'
			settings = json.loads((local / 'Settings.json').read_text())
			self.assertNotIn('error_reports', settings)
			self.assertNotIn('usage_metrics', settings)
			self.assertTrue(settings['scripting_api']['automation'])
			self.assertFalse((local / 'Session.json').exists())

	def test_launch_creates_large_left_fixture_and_core_settings(self):
		with TemporaryDirectory() as temp:
			session = self._launch(
				temp, large=3, core_settings='{"file_age_style": "tint"}')
			self.assertIn(
				call(session, 'POST', '/v1/window', {'width': 1280, 'height': 800}),
				self.api_calls)
			self.assertEqual(1, len(self.api_calls))
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

	def test_launch_creates_and_reports_network_share_when_requested(self):
		with TemporaryDirectory() as temp, \
			patch('network_share.Path.is_dir', return_value=True):
			session = self._launch(temp, network_share=True)
			self.assertTrue(session['network_share'].startswith(
				'network://localhost/D$/'))
			self.assertTrue(session['network_share'].endswith('/share'))
			self.assertTrue(session['network_share_unc'].endswith('\\share'))
			self.assertTrue((Path(session['profile']).parent / 'share' /
				'visible.txt').is_file())

	def test_launch_with_caller_left_does_not_create_deep_fixture(self):
		with TemporaryDirectory() as temp:
			left = Path(temp) / 'provided-left'
			left.mkdir()
			session = self._launch(temp, deep=2, left=str(left))
			self.assertNotIn('deep', session)
			self.assertFalse((left / 'deep').exists())

		with TemporaryDirectory() as temp, \
			patch.object(fman_ui, 'detached_popen',
				wraps=fman_ui.detached_popen) as detached:
			session = self._launch(temp, previous_version='1.0.0')
			settings = json.loads((Path(session['profile']) / 'Local' /
				'Session.json').read_text(encoding='utf-8'))
		self.assertEqual('1.0.0', settings['fman_version'])
		self.assertEqual(2, detached.call_count)

	def test_start_fman_resizes_after_state_is_reachable(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			root.mkdir()
			session = {
				'profile': str(root / 'profile'), 'left': str(root / 'left'),
				'right': str(root / 'right'), 'port': 123,
			}
			state = {'ok': True}
			with patch.object(fman_ui.subprocess, 'Popen') as popen, \
				patch.object(fman_ui, 'process_start_time', return_value=3.0), \
				patch.object(fman_ui, 'fman_process_identity', return_value=None), \
				patch.object(fman_ui, '_wait_for_state', return_value=state), \
				patch.object(fman_ui, 'read_startup_prompts', return_value={
					'demo_mode': False, 'update_check_scheduled': True,
					'dialog': None,
				}), \
				patch.object(fman_ui, '_api', return_value={
					'width': 1280, 'height': 768,
					'available_width': 1920, 'available_height': 1080,
				}) as api:
				popen.return_value.pid = 21
				result = fman_ui._start_fman(session, root)
		self.assertEqual((1280, 768), (
			result['window']['width'], result['window']['height']))
		api.assert_called_once_with(session, 'POST', '/v1/window', {
			'width': 1280, 'height': 800,
		})

	def test_start_fman_passes_demo_argument_when_session_has_demo(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			root.mkdir()
			session = {
				'profile': str(root / 'profile'), 'left': str(root / 'left'),
				'right': str(root / 'right'), 'port': 123, 'demo': 1,
			}
			with patch.object(fman_ui, 'detached_popen') as popen, \
				patch.object(fman_ui, 'process_start_time', return_value=3.0), \
				patch.object(fman_ui, 'fman_process_identity', return_value=None), \
				patch.object(fman_ui, '_wait_for_state', return_value={}), \
				patch.object(fman_ui, 'read_startup_prompts',
					return_value={'demo_mode': True, 'update_check_scheduled': False,
						'dialog': None}, create=True), \
				patch.object(fman_ui, '_api', return_value={
					'width': 1280, 'height': 768,
					'available_width': 1920, 'available_height': 1080,
				}):
				popen.return_value.pid = 21
				result = fman_ui._start_fman(session, root)
		self.assertEqual(['--automation-demo', '1'],
			popen.call_args.args[0][-2:])
		self.assertTrue(result['startup_prompts']['demo_mode'])
		self.assertEqual(result['startup_prompts'], session['startup_prompts'])

	def test_start_fman_does_not_pass_demo_argument_without_session_demo(self):
		with TemporaryDirectory() as temp:
			root = Path(temp) / 'session'
			root.mkdir()
			session = {
				'profile': str(root / 'profile'), 'left': str(root / 'left'),
				'right': str(root / 'right'), 'port': 123,
			}
			with patch.object(fman_ui, 'detached_popen') as popen, \
				patch.object(fman_ui, 'process_start_time', return_value=3.0), \
				patch.object(fman_ui, 'fman_process_identity', return_value=None), \
				patch.object(fman_ui, '_wait_for_state', return_value={}), \
				patch.object(fman_ui, 'read_startup_prompts',
					return_value={'demo_mode': False,
						'update_check_scheduled': True, 'dialog': None}, create=True), \
				patch.object(fman_ui, '_api', return_value={
					'width': 1280, 'height': 768,
					'available_width': 1920, 'available_height': 1080,
				}):
				popen.return_value.pid = 21
				fman_ui._start_fman(session, root)
		self.assertNotIn('--automation-demo', popen.call_args.args[0])

	def test_demo_launch_leaves_consent_unanswered_and_saves_demo_id(self):
		with TemporaryDirectory() as temp, \
			patch.object(fman_ui, 'read_startup_prompts', return_value={
				'demo_mode': True, 'update_check_scheduled': False, 'dialog': None,
			}, create=True):
			session = self._launch(temp, demo=1)
			settings = json.loads((Path(session['profile']) / 'Local' /
				'Settings.json').read_text(encoding='utf-8'))
			self.assertNotIn('error_reports', settings)
			self.assertNotIn('usage_metrics', settings)
			self.assertEqual(1, session['demo'])
			self.assertTrue((Path(session['profile']) / 'Local' /
				'Session.json').exists())
			self.assertIn('startup_prompts', session)

	def test_invalid_launch_options_fail_before_session_directory_is_created(self):
		with TemporaryDirectory() as temp, patch.dict(os.environ, {'TEMP': temp}):
			for args in (
				SimpleNamespace(left=None, right=None, large=-1, deep=0, archive=0,
					core_settings=None),
				SimpleNamespace(left=None, right=None, large=0, deep=0, archive=0,
					core_settings='[1]'),
				SimpleNamespace(left=None, right=None, large=0, deep=-1, archive=0,
					core_settings=None, previous_version=None),
				SimpleNamespace(left=None, right=None, large=0, deep=5001, archive=0,
					core_settings=None, previous_version=None),
				SimpleNamespace(left=None, right=None, large=0, deep=0, archive=0,
					core_settings=None, previous_version=' '),
				SimpleNamespace(left=None, right=None, large=0, deep=0, archive=0,
					core_settings=None, previous_version=''),
				SimpleNamespace(left=None, right=None, large=0, deep=0, archive=0,
					core_settings=None, previous_version='1.0.0',
					first_start=True),
			):
				with self.subTest(args=args), self.assertRaises(ValueError):
					fman_ui._launch(args)
				self.assertFalse((Path(temp) / 'fman-ui').exists())
