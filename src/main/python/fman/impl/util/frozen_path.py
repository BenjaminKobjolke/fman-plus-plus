"""Remove bundled folders from PATH inherited by child processes."""

import os


def remove_dirs_below(path_value: str, root: str) -> str:
	root_path = os.path.normcase(os.path.normpath(root))
	root_prefix = root_path + os.sep
	entries = path_value.split(os.pathsep)
	return os.pathsep.join(
		entry for entry in entries
		if not (
			(entry_path := os.path.normcase(os.path.normpath(entry))) == root_path
			or entry_path.startswith(root_prefix)
		)
	)
