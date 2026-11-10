"""Choose Windows drag-and-drop actions using Explorer semantics.

Across volumes Windows Explorer copies by default (upstream fman issue #459).
"""

import ntpath
from typing import Optional, Sequence, Tuple

from fman.impl.util.qt import ControlModifier, CopyAction, MoveAction, ShiftModifier
from fman.url import splitscheme


def volume_of(url: str) -> Tuple[str, str]:
	"""Return the URL scheme and, for local files, drive or UNC share."""
	scheme, path = splitscheme(url)
	if scheme == 'file://':
		# fman file URLs retain a leading slash before drive letters, unlike
		# Windows paths. UNC URLs already have the two leading slashes splitdrive
		# expects.
		if len(path) >= 3 and path[0] == '/' and path[2] == ':':
			path = path[1:]
		return scheme, ntpath.splitdrive(path)[0].lower()
	return scheme, ''


def is_cross_volume(src_urls: Sequence[str], dest_url: Optional[str]) -> bool:
	"""Return whether any source and the destination are on different volumes."""
	if dest_url is None or not src_urls:
		return False
	dest_volume = volume_of(dest_url)
	return any(volume_of(url) != dest_volume for url in src_urls)


def choose_drop_action(
		modifiers: int, src_urls: Sequence[str], dest_url: Optional[str]) -> int:
	"""Choose the Qt drop action from modifiers and source/destination URLs."""
	if modifiers & ControlModifier:
		return CopyAction
	if modifiers & ShiftModifier:
		return MoveAction
	if is_cross_volume(src_urls, dest_url):
		return CopyAction
	return MoveAction
