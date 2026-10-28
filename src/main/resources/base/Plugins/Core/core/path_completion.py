"""Folder-name completion for paths entered in destination prompts."""
from fman.url import join, splitscheme

import fman.fs
import os


def complete_path(text, dest_dir, src_dir=None, fs=fman.fs):
	"""Return matching folder paths, preserving the path prefix as typed."""
	try:
		splitscheme(text)
	except ValueError:
		url_input = False
	else:
		url_input = True

	sep = '/' if url_input else os.sep
	separators = ('/',) if url_input else ('/', os.sep)
	last_sep = max((text.rfind(char) for char in separators), default=-1)
	head = text[:last_sep + 1]
	partial = text[last_sep + 1:]
	from core.commands.transfer import _from_human_readable
	folder = _from_human_readable(head, dest_dir, src_dir)

	try:
		matches = []
		for name in fs.iterdir(folder):
			if not name.casefold().startswith(partial.casefold()):
				continue
			try:
				if fs.is_dir(join(folder, name)):
					matches.append(name)
			except OSError:
				continue
	except OSError:
		return []

	return [head + name + sep for name in sorted(matches, key=str.casefold)]
