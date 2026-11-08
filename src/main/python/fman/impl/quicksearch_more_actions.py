"""Make Enter and Shift+Enter discoverable in palettes that support both."""
from fman import translate
from fman.localization_keys import QUICKSEARCH_KEY_ENTER, QUICKSEARCH_KEY_SHIFT_ENTER, \
	QUICKSEARCH_MORE_ACTIONS, QUICKSEARCH_RUN
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QFontMetricsF


MORE_GLYPH = '⋯'


def footer_text():
	return '%s  %s    %s  %s' % (
		translate(QUICKSEARCH_KEY_ENTER),
		translate(QUICKSEARCH_RUN),
		translate(QUICKSEARCH_KEY_SHIFT_ENTER),
		translate(QUICKSEARCH_MORE_ACTIONS),
	)


def more_button_rect(row_rect, padding_right, font):
	row_rect = QRectF(row_rect)
	width = QFontMetricsF(font).horizontalAdvance(MORE_GLYPH) + padding_right
	return QRectF(
		row_rect.right() - padding_right - width,
		row_rect.center().y() - width / 2,
		width,
		width,
	)


def is_more_click(row_rect, pos, padding_right, font):
	return more_button_rect(row_rect, padding_right, font).contains(pos)
