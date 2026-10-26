"""Remove only Recycle Bin entries created by a disposable UI session."""

import ntpath
import os
from pathlib import Path
import sys


def _is_windows():
	return os.name == 'nt'


def _load_recycle_bin():
	project_root = Path(__file__).resolve().parents[2]
	import_roots = (
		project_root / 'src' / 'main' / 'python',
		project_root / 'src' / 'main' / 'resources' / 'base' / 'Plugins' / 'Core',
	)
	for import_root in import_roots:
		if str(import_root) not in sys.path:
			sys.path.insert(0, str(import_root))
	from core import recycle_bin
	return recycle_bin


def cleanup_session(session_root):
	"""Remove trash entries whose original paths belong to this session."""
	if not _is_windows():
		return 0

	recycle_bin = _load_recycle_bin()
	root = ntpath.normpath(str(session_root)).casefold()
	removed = 0
	for entry in recycle_bin.iter_entries(str(session_root)):
		original_path = ntpath.normpath(entry.original_path).casefold()
		try:
			within_session = ntpath.commonpath((root, original_path)) == root
		except ValueError:
			continue
		if not within_session:
			continue
		try:
			recycle_bin.remove_entry(entry)
		except OSError:
			continue
		removed += 1
	return removed
