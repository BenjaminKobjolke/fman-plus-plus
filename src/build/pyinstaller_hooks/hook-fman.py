"""Plugins expect the full Python standard library (upstream issue #193)."""

import sys
import sysconfig
from pathlib import Path


# These modules are build tools or a conflicting GUI toolkit, not plugin libraries.
EXCLUDED = frozenset({
	'tkinter',
	'_tkinter',
	'turtle',
	'turtledemo',
	'idlelib',
	'test',
	'tests',
	'ensurepip',
	'venv',
	'lib2to3',
})


def _stdlib_source_modules() -> set[str]:
	stdlib_path = Path(sysconfig.get_paths()['stdlib'])
	modules = set()
	for path in stdlib_path.rglob('*.py'):
		parts = path.relative_to(stdlib_path).parts
		if (
			not parts
			or parts[0] in EXCLUDED
			or 'site-packages' in parts
			or any(part in {'test', 'tests', '__pycache__'} for part in parts)
		):
			continue

		module_parts = (
			parts[:-1]
			if parts[-1] == '__init__.py'
			else (*parts[:-1], path.stem)
		)
		if (
			not module_parts
			or module_parts[0] in EXCLUDED
			or module_parts[0].startswith('_test')
		):
			continue
		modules.add('.'.join(module_parts))
	return modules


# sys.stdlib_module_names includes test packages, so apply the same exclusions here.
hiddenimports = sorted(
	_stdlib_source_modules()
	| {
		name
		for name in sys.stdlib_module_names
		if name not in EXCLUDED
		and not name.startswith(
			(
				'tkinter', '_tkinter', 'turtle', 'idlelib', 'test', 'ensurepip', 'venv',
				'_test',
			)
		)
	}
)
