import os
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless


@skipUnless(os.name == 'nt', 'The portable swap helper uses Windows tools')
class PortableUpdateScriptTest(TestCase):
	def test_replaces_version_files_and_preserves_user_data(self):
		with tempfile.TemporaryDirectory() as directory:
			root = Path(directory)
			source = root / 'update' / 'fman++'
			target = root / 'portable'
			(source / 'Plugins' / 'Core').mkdir(parents=True)
			(target / 'Plugins' / 'Core').mkdir(parents=True)
			(target / 'Data').mkdir()
			(source / 'Plugins' / 'Core' / 'new.txt').write_text(
					'new', encoding='utf-8'
			)
			(target / 'Plugins' / 'Core' / 'stale.txt').write_text(
					'stale', encoding='utf-8'
			)
			(source / 'fman.exe').write_text('new exe', encoding='utf-8')
			(source / 'portable.txt').write_text('new marker', encoding='utf-8')
			(target / 'portable.txt').write_text('user marker', encoding='utf-8')
			(target / 'notes.txt').write_text('user file', encoding='utf-8')
			(target / 'Data' / 'settings.json').write_text('settings', encoding='utf-8')
			helper = Path(__file__).parents[2] / 'bin' / 'windows'
			helper /= 'portable_update.ps1'
			result = subprocess.run(
				[
					'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
					'-File', str(helper),
				'-ProcessId', str(2**31 - 1),
					'-Source', str(source),
					'-Target', str(target),
				],
				capture_output=True,
				text=True,
				timeout=180,
			)

			self.assertEqual(0, result.returncode, result.stdout + result.stderr)
			self.assertEqual(
					'new', (target / 'Plugins' / 'Core' / 'new.txt').read_text()
			)
			self.assertFalse((target / 'Plugins' / 'Core' / 'stale.txt').exists())
			self.assertEqual('new exe', (target / 'fman.exe').read_text())
			self.assertEqual('user marker', (target / 'portable.txt').read_text())
			self.assertEqual('user file', (target / 'notes.txt').read_text())
			self.assertEqual(
					'settings', (target / 'Data' / 'settings.json').read_text()
			)
			self.assertFalse(source.exists())
