"""Qt-free helpers used by Core's folder tree."""

from core.commands.hidden_files import _is_hidden_file
from fman import fs
from fman.url import basename, dirname, join, splitscheme


FOLLOW_CURSOR_KEY = 'tree_follow_cursor'
FOLLOW_CURSOR_DELAY_MS = 300


def tree_ancestors(url):
	"""Return a URL's ancestors from its scheme root down to the URL."""
	ancestors = [url]
	while True:
		parent = dirname(ancestors[-1])
		if parent == ancestors[-1] or parent == splitscheme(parent)[0]:
			break
		ancestors.append(parent)
	ancestors.reverse()
	return ancestors


def list_subfolders(url, show_hidden):
	"""List readable child folders, sorted by name without case sensitivity."""
	try:
		return _list_subfolders_at(url, show_hidden)
	except OSError:
		try:
			resolved_url = fs.resolve(url)
		except OSError:
			return []
		if resolved_url == url:
			return []
		try:
			return _list_subfolders_at(resolved_url, show_hidden)
		except OSError:
			return []


def _list_subfolders_at(url, show_hidden):
	"""List children at one location; the caller handles listing failures."""
	folders = []
	for name in fs.iterdir(url):
		child_url = join(url, name)
		try:
			if not fs.is_dir(child_url):
				continue
		except OSError:
			continue
		if not show_hidden and _is_hidden_file(child_url):
			continue
		folders.append(child_url)
	return sorted(folders, key=lambda child_url: basename(child_url).casefold())


def can_drop(file_urls, dest_dir):
	"""Return whether a drop can move or copy files into the destination."""
	file_urls = list(file_urls)
	if not file_urls or all(dirname(url) == dest_dir for url in file_urls):
		return False
	ancestors = set(tree_ancestors(dest_dir))
	return not any(url in ancestors for url in file_urls)
