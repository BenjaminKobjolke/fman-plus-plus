"""Shorten long paths by replacing middle folder names with ellipses."""

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Tuple


ELLIPSIS = '…'
_FOLDER = re.compile(r'[^\\/]+')


@dataclass(frozen=True)
class ShortenedPath:
	"""A displayed path and the original name ranges hidden by its ellipses."""

	text: str
	hidden: Tuple[Tuple[int, int], ...]

	def shown_index(self, original: int) -> Optional[int]:
		"""Map an original character index to the shown text, if visible."""
		removed = 0
		for start, stop in self.hidden:
			if original < start:
				return original - removed
			if start <= original < stop:
				return None
			removed += stop - start - 1
		return original - removed

	def original_index(self, shown: int) -> int:
		"""Map a shown character index back to its original path position."""
		removed = 0
		for start, stop in self.hidden:
			ellipsis = start - removed
			if shown <= ellipsis:
				return shown + removed if shown < ellipsis else start
			removed += stop - start - 1
		return shown + removed

	def hidden_at(self, shown: int) -> Optional[Tuple[int, int]]:
		"""Return the original name range represented by a shown ellipsis."""
		removed = 0
		for start, stop in self.hidden:
			if shown == start - removed:
				return start, stop
			removed += stop - start - 1
		return None


def _merge_ranges(ranges: Iterable[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
	merged = []
	for start, stop in sorted(ranges):
		if merged and start <= merged[-1][1] + 1:
			merged[-1] = merged[-1][0], stop
		else:
			merged.append((start, stop))
	return tuple(merged)


def _build(path: str, hidden: Tuple[Tuple[int, int], ...]) -> ShortenedPath:
	parts = []
	position = 0
	for start, stop in hidden:
		parts.extend((path[position:start], ELLIPSIS))
		position = stop
	parts.append(path[position:])
	return ShortenedPath(''.join(parts), hidden)


def shorten_path(
	path: str, fits: Callable[[str], bool], keep: Iterable[int] = ()
) -> Optional[ShortenedPath]:
	"""Hide middle folder names until the path fits, preserving useful ends."""
	folders = list(_FOLDER.finditer(path))
	if len(folders) < 4:
		return None
	if fits(path):
		return ShortenedPath(path, ())

	keep = tuple(keep)
	head_end = folders[1].end()
	last_start = folders[-1].start()
	candidates = [
		folder for folder in folders
		if folder.start() >= head_end
		and folder.start() < last_start
		and not any(folder.start() <= index < folder.end() for index in keep)
	]
	if not candidates:
		return None

	hidden = []
	for folder in candidates:
		hidden.append((folder.start(), folder.end()))
		result = _build(path, _merge_ranges(hidden))
		if fits(result.text):
			return result
	return _build(path, _merge_ranges(hidden))
