from typing import List, Tuple

from fman.impl.path_shortening import shorten_path
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics


def elide_title_left(title, font, available_width):
	metrics = QFontMetrics(font)
	if metrics.horizontalAdvance(title) <= available_width:
		return title, 0
	elided = metrics.elidedText(title, Qt.ElideLeft, int(max(0, available_width)))
	removed_chars = len(title) - (len(elided) - 1)
	return elided, removed_chars


def shift_highlight(highlight, removed_chars):
	if not removed_chars:
		return list(highlight)
	return [index - removed_chars + 1 for index in highlight if index >= removed_chars]


def elide_title(
	title: str, highlight: List[int], font: QFont, available_width: float
) -> Tuple[str, List[int]]:
	"""Shorten path titles first, then use Qt's left elision as a fallback."""
	metrics = QFontMetrics(font)

	def fits(text: str) -> bool:
		return metrics.horizontalAdvance(text) <= available_width

	if fits(title):
		return title, list(highlight)

	shortened = shorten_path(title, fits, keep=highlight)
	if shortened is None:
		shortened_title = title
		shortened_highlight = list(highlight)
	else:
		shortened_title = shortened.text
		shortened_highlight = []
		for index in highlight:
			shown = shortened.shown_index(index)
			if shown is not None:
				shortened_highlight.append(shown)

	shown_title, removed_chars = elide_title_left(
		shortened_title, font, available_width
	)
	return shown_title, shift_highlight(shortened_highlight, removed_chars)
