"""Helpers for mapping displayed location text to its parent folders."""

from dataclasses import dataclass
from typing import List, Optional

from fman.url import as_human_readable, dirname, splitscheme


@dataclass(frozen=True)
class LocationSegment:
	url: str
	end: int


def location_segments(url: str) -> List[LocationSegment]:
	"""Return displayed parent-folder prefixes, from root to nearest parent."""
	displayed_url = as_human_readable(url)
	ancestors = []
	ancestor_url = dirname(url)
	while ancestor_url != url:
		_, path = splitscheme(ancestor_url)
		if not path:
			break
		displayed_ancestor = as_human_readable(ancestor_url)
		if displayed_url.startswith(displayed_ancestor):
			ancestors.append(LocationSegment(ancestor_url, len(displayed_ancestor)))
		url, ancestor_url = ancestor_url, dirname(ancestor_url)
	ancestors.reverse()
	return ancestors


def segment_at(
	segments: List[LocationSegment], position: int
) -> Optional[LocationSegment]:
	"""Return the parent-folder prefix covering a character position."""
	if position < 0:
		return None
	for segment in segments:
		if position < segment.end:
			return segment
	return None


def child_on_path(parent_url: str, current_url: str) -> Optional[str]:
	"""Return the immediate descendant of parent_url leading to current_url."""
	if splitscheme(parent_url)[0] != splitscheme(current_url)[0]:
		return None
	child_url = current_url
	while child_url != parent_url:
		parent_of_child = dirname(child_url)
		if parent_of_child == child_url:
			return None
		if parent_of_child == parent_url:
			return child_url
		child_url = parent_of_child
	return None
