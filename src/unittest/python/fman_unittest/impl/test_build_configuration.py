import ast
import json
import runpy
import unittest
from pathlib import Path


def _python_files(root):
	return (
		path for path in root.rglob('*.py')
		if 'tests' not in path.parts
	)


def _module_name(path, root, package_name):
	parts = list(path.relative_to(root).with_suffix('').parts)
	if parts[-1] == '__init__':
		parts.pop()
	return '.'.join((package_name, *parts))


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

	def test_plugin_fman_impl_imports_reach_the_freeze(self):
		project_root = Path(__file__).resolve().parents[5]
		python_root = project_root / 'src' / 'main' / 'python'
		impl_root = python_root / 'fman' / 'impl'
		plugin_root = project_root / 'src' / 'main' / 'resources' / 'base' / 'Plugins'
		plugin_modules = set()

		for path in _python_files(plugin_root):
			tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					plugin_modules.update(
						alias.name for alias in node.names
						if alias.name.startswith('fman.impl')
					)
				elif (
					isinstance(node, ast.ImportFrom)
					and node.level == 0
					and node.module is not None
					and node.module.startswith('fman.impl')
				):
					plugin_modules.add(node.module)
					if node.module == 'fman.impl':
						for alias in node.names:
							if alias.name == '*':
								continue
							module_path = impl_root / alias.name
							if (
								module_path.with_suffix('.py').is_file()
								or (module_path / '__init__.py').is_file()
							):
								plugin_modules.add(f'fman.impl.{alias.name}')

		main_modules = set()
		main_root = python_root / 'fman'
		for path in _python_files(main_root):
			current_module = _module_name(path, main_root, 'fman')
			current_parts = current_module.split('.')
			package_parts = (
				current_parts if path.name == '__init__.py' else current_parts[:-1]
			)
			tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
			for node in ast.walk(tree):
				if isinstance(node, ast.Import):
					main_modules.update(alias.name for alias in node.names)
				elif isinstance(node, ast.ImportFrom):
					if node.level:
						base_parts = package_parts[:len(package_parts) - node.level + 1]
						if node.module:
							base_parts.extend(node.module.split('.'))
						base_module = '.'.join(base_parts)
					else:
						if node.module is None:
							continue
						base_module = node.module

					if base_module != current_module:
						main_modules.add(base_module)
					for alias in node.names:
						if alias.name == '*':
							continue
						imported_module = f'{base_module}.{alias.name}'
						if imported_module != current_module:
							main_modules.add(imported_module)

		hidden_imports = set()
		settings_root = project_root / 'src' / 'build' / 'settings'
		for settings_path in settings_root.glob('*.json'):
			with settings_path.open(
				encoding='utf-8'
			) as settings_file:
				hidden_imports.update(
					json.load(settings_file).get('hidden_imports', [])
				)

		# shortcut: "imported by the main app" ignores whether that importer is
		# itself reachable from main; upgrade to a PyInstaller module-graph check
		# if a gap slips through.
		for module in sorted(plugin_modules):
			with self.subTest(module=module):
				self.assertTrue(
					module in main_modules or module in hidden_imports,
					f'{module} is imported only by a bundled plugin; add it to '
					'hidden_imports in src/build/settings/base.json',
				)


if __name__ == '__main__':
	unittest.main()
