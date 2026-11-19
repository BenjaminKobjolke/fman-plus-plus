"""Tests for the isolated Windows installer update driver."""

import json
from pathlib import Path
import re
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, skipUnless
from unittest.mock import patch

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent / 'fman_ui'))
import installer_session
import installer_processes
import installer_snapshot
import native_dialogs
import session_reaper
from parser import parser


class FakeRegistry:
	def __init__(self, values=None, keys=None):
		self.values = dict(values or {})
		self.keys = set(keys or ())

	def read_value(self, key, name):
		return self.values.get((key, name))

	def write_value(self, key, name, value, value_type):
		self.values[(key, name)] = (value, value_type)

	def delete_value(self, key, name):
		self.values.pop((key, name), None)

	def key_exists(self, key):
		return key in self.keys

	def delete_key(self, key):
		self.keys.discard(key)


def _dialogs_for_process_tree(pid):
	# The venv python.exe is a launcher; the real interpreter child owns the window.
	try:
		children = psutil.Process(pid).children(recursive=True)
	except psutil.NoSuchProcess:
		children = []
	return [dialog for process_id in [pid, *(child.pid for child in children)]
		for dialog in native_dialogs.dialogs_for_process(process_id)]


class InstallerParserTest(TestCase):
	def test_parses_all_actions_and_answer_choices(self):
		cases = (
			(['installer', 'launch', '--setup', 'X', '--windows', '2'],
				('launch', None, 2)),
			(['installer', 'update'], ('update', None, 2)),
			(['installer', 'state'], ('state', None, 2)),
			(['installer', 'close-window', '--index', '0'],
				('close-window', None, 2)),
			(['installer', 'answer', 'retry'], ('answer', 'retry', 2)),
			(['installer', 'answer', 'cancel'], ('answer', 'cancel', 2)),
			(['installer', 'cleanup'], ('cleanup', None, 2)),
		)
		for argv, expected in cases:
			with self.subTest(argv=argv):
				args = parser().parse_args(argv)
				self.assertEqual('installer', args.action)
				self.assertEqual(expected, (
					args.installer_action, getattr(args, 'choice', None),
					getattr(args, 'windows', 2)))

	def test_answer_rejects_other_choices(self):
		with self.assertRaises(SystemExit):
			parser().parse_args(['installer', 'answer', 'other'])


class InstallerSnapshotTest(TestCase):
	def test_round_trip_restores_path_shortcuts_and_absent_keys(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			shortcut = root / 'fman++.lnk'
			shortcut.write_bytes(b'existing shortcut')
			missing = root / 'fman.lnk'
			registry = FakeRegistry(
				{(installer_snapshot.ENVIRONMENT_KEY, 'Path'): ('old-path', 2)},
				{installer_snapshot.FMAN_KEY},
			)
			with patch.object(installer_snapshot, 'shortcut_paths',
					return_value=(shortcut, missing)):
				snapshot = installer_snapshot.take_snapshot(registry)
				shortcut.write_bytes(b'changed')
				missing.write_bytes(b'created')
				registry.write_value(installer_snapshot.ENVIRONMENT_KEY,
					'Path', 'changed', 1)
				registry.keys.update({installer_snapshot.UNINSTALL_KEY})
				installer_snapshot.restore_snapshot(snapshot, registry)
			self.assertEqual(b'existing shortcut', shortcut.read_bytes())
			self.assertFalse(missing.exists())
			self.assertEqual(('old-path', 2), registry.read_value(
				installer_snapshot.ENVIRONMENT_KEY, 'Path'))
			self.assertEqual({installer_snapshot.FMAN_KEY}, registry.keys)


class InstallerSessionTest(TestCase):
	def test_setup_command_keeps_install_dir_last_and_uses_run_as_invoker(self):
		command = installer_session.setup_command('setup.exe', 'C:/temp/app')
		self.assertEqual(['setup.exe', '/S', '/CurrentUser', '/D=C:/temp/app'], command)
		self.assertEqual('C:/temp/app', command[-1].split('=', 1)[1])
		self.assertEqual('RunAsInvoker',
			installer_session.setup_environment({})['__COMPAT_LAYER'])

	def test_profile_preparation_writes_portable_profile_and_sentinel(self):
		with TemporaryDirectory() as temp:
			app = Path(temp) / 'app'
			app.mkdir()
			installer_session.prepare_profile(app)
			self.assertTrue((app / 'portable.txt').is_file())
			settings = json.loads((app / 'Data/Local/Settings.json').read_text())
			self.assertEqual({
				'single_instance': False, 'error_reports': False,
				'usage_metrics': False,
			}, settings)
			session = json.loads((app / 'Data/Local/Session.json').read_text())
			self.assertEqual(2, len(session['panes']))
			sentinel = app / 'Plugins/Core/fman_ui_installer_sentinel.txt'
			self.assertTrue(sentinel.is_file())

	def test_launch_refuses_unsafe_or_unavailable_setup_without_running_it(self):
		for platform, exists, key_exists in (
			('nt', True, True), ('nt', False, False), ('posix', True, False),
		):
			with self.subTest(platform=platform, exists=exists,
					key_exists=key_exists), \
				patch.object(installer_session.os, 'name', platform), \
				patch.object(installer_session.Path, 'is_file', return_value=exists), \
				patch.object(installer_session, 'registry') as registry, \
				patch.object(installer_session.subprocess, 'run') as run:
				registry.key_exists.return_value = key_exists
				with self.assertRaises((OSError, RuntimeError, ValueError)):
					installer_session.launch('setup.exe')
				run.assert_not_called()

	def test_state_reads_waiter_exit_and_process_start_relative_to_update(self):
		with TemporaryDirectory() as temp:
			root = Path(temp)
			app = root / 'app'
			app.mkdir()
			session = {
				'install_dir': str(app), 'setup_pid': 45, 'waiter_pid': 44,
				'update_started_at': 100.0, 'session_dir': str(root),
			}
			(root / 'installer_exit.json').write_text(
				json.dumps({'exit_code': 2, 'ended_at': 110.0}))
			(root / 'installer.json').write_text(json.dumps(session))
			processes = [
				SimpleNamespace(pid=1, create_time=lambda: 99.0,
					exe=lambda: str(app / 'fman.exe')),
				SimpleNamespace(pid=2, create_time=lambda: 101.0,
					exe=lambda: str(app / 'fman.exe')),
			]
			with patch.object(
					installer_session, '_load_session', return_value=session), \
				patch.object(
					installer_processes.psutil, 'process_iter',
					return_value=processes), \
				patch.object(
					installer_processes, 'window_titles',
					side_effect=[['one'], ['two']]), \
				patch.object(
					installer_session, 'read_file_version', return_value='1.2.3'), \
				patch.object(installer_session.time, 'time', return_value=111.0):
				result = installer_session.state()
			self.assertEqual(2, result['installer']['exit_code'])
			self.assertEqual([False, True], [
				p['started_after_update'] for p in result['fman_processes']])

	def test_answer_refuses_when_setup_dialog_is_not_open(self):
		session = {'setup_pid': 45}
		with patch.object(installer_session, '_load_session', return_value=session), \
			patch.object(installer_session, 'dialogs_for_process', return_value=[]):
			with self.assertRaisesRegex(RuntimeError, 'dialog'):
				installer_session.answer('retry')

	@skipUnless(sys.platform == 'win32', 'Win32 dialog integration test')
	def test_reads_and_clicks_real_retry_and_cancel_dialogs(self):
		for label, control_id in (('Retry', 4), ('Cancel', 2)):
			code = (
				"import ctypes, sys; "
				"sys.exit(ctypes.windll.user32.MessageBoxW(None, 'text', 'title', "
				"0x00000005 | 0x00040000))"
			)
			process = subprocess.Popen([sys.executable, '-c', code])
			process_start_time = psutil.Process(process.pid).create_time()
			try:
				deadline = time.monotonic() + 10
				dialogs = []
				while time.monotonic() < deadline:
					dialogs = _dialogs_for_process_tree(process.pid)
					if dialogs:
						break
					time.sleep(.1)
				if not dialogs:
					exit_code = process.poll()
					# A zero MessageBoxW result means Windows exposed no dialog
					# to this process.
					if exit_code is None or exit_code == 0:
						self.skipTest(
							('no interactive desktop exposed the child MessageBoxW '
							 'window'))
				self.assertTrue(dialogs, 'MessageBoxW did not appear within 10 seconds')
				dialog = dialogs[0]
				self.assertEqual(('title', 'text', True),
					(dialog.title, dialog.text, dialog.topmost))
				self.assertEqual({'Retry', 'Cancel'},
					{button.label for button in dialog.buttons})
				native_dialogs.click_dialog_button(dialog, control_id)
				self.assertEqual(control_id, process.wait(timeout=5))
			finally:
				if process.poll() is None:
					session_reaper.kill_process(process.pid, process_start_time)
					process.wait(timeout=5)

	@skipUnless(sys.platform == 'win32', 'Windows file version API')
	def test_file_version_is_a_dotted_string(self):
		version = native_dialogs.read_file_version(sys.executable)
		self.assertRegex(version, re.compile(r'^\d+(\.\d+)+$'))


if __name__ == '__main__':
	from unittest import main
	main()
