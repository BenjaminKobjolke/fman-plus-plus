import json
import runpy
import unittest
from pathlib import Path


class BuildConfigurationTest(unittest.TestCase):
	def test_windows_hidden_imports_include_network_constants(self):
		project_root = Path(__file__).resolve().parents[5]
		settings_path = (
			project_root / 'src' / 'build' / 'settings' / 'windows.json'
		)
		with settings_path.open(encoding='utf-8') as settings_file:
			settings = json.load(settings_file)

		self.assertIn('win32netcon', settings['hidden_imports'])

	def test_standard_library_hook_includes_public_modules(self):
		project_root = Path(__file__).resolve().parents[5]
		hook_path = (
			project_root / 'src' / 'build' / 'pyinstaller_hooks' / 'hook-fman.py'
		)
		hiddenimports = runpy.run_path(str(hook_path))['hiddenimports']

		for module in (
			'sqlite3',
			'email.mime.text',
			'html.parser',
			'wsgiref.simple_server',
			'xmlrpc.server',
			'graphlib',
			'_sqlite3',
		):
			with self.subTest(module=module):
				self.assertIn(module, hiddenimports)

		for module in hiddenimports:
			with self.subTest(module=module):
				self.assertFalse(
					module.startswith(
						(
							'tkinter', '_tkinter', 'turtle', 'idlelib', 'test',
							'ensurepip', 'venv', '_test',
						)
					)
					or any(part == 'tests' for part in module.split('.'))
				)

	def test_standard_library_hook_imports_are_sorted_and_unique(self):
		project_root = Path(__file__).resolve().parents[5]
		hook_path = (
			project_root / 'src' / 'build' / 'pyinstaller_hooks' / 'hook-fman.py'
		)
		hiddenimports = runpy.run_path(str(hook_path))['hiddenimports']

		self.assertEqual(hiddenimports, sorted(hiddenimports))
		self.assertEqual(hiddenimports, list(dict.fromkeys(hiddenimports)))

	def test_pyinstaller_uses_standard_library_hook_directory(self):
		project_root = Path(__file__).resolve().parents[5]
		settings_path = project_root / 'src' / 'build' / 'settings' / 'base.json'
		with settings_path.open(encoding='utf-8') as settings_file:
			settings = json.load(settings_file)

		args = settings['extra_pyinstaller_args']
		index = args.index('--additional-hooks-dir')
		self.assertEqual(
			args[index + 1], '${project_dir}/src/build/pyinstaller_hooks'
		)


if __name__ == '__main__':
	unittest.main()
