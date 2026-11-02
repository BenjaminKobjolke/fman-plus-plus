from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics


def elide_title_left(title, font, available_width):
	metrics = QFontMetrics(font)
	if metrics.horizontalAdvance(title) <= available_width:
		return title, 0
	elided = metrics.elidedText(title, Qt.ElideLeft, max(0, available_width))
	removed_chars = len(title) - (len(elided) - 1)
	return elided, removed_chars


def shift_highlight(highlight, removed_chars):
	if not removed_chars:
		return list(highlight)
	return [index - removed_chars + 1 for index in highlight if index >= removed_chars]
