"""Place the sorted header arrow relative to its label in Qt's drawing hooks.

QSS positions arrow subcontrols relative to the whole section, so it cannot
keep the arrow beside the text when a column changes width.
"""

from enum import Enum
from typing import NamedTuple

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QHeaderView, QStyle, QStyleOptionHeader


SORT_ARROW_SETTING = 'sort_arrow_position'


class SortArrowPosition(Enum):
	AFTER = 'after'
	BEFORE = 'before'
	EDGE = 'edge'

	@classmethod
	def from_setting(cls, value: object) -> 'SortArrowPosition':
		try:
			return cls(value)
		except (TypeError, ValueError):
			return cls.AFTER


class HeaderPlacement(NamedTuple):
	arrow: QRect
	label: QRect


def place_sort_arrow(
	position: SortArrowPosition,
	label_rect: QRect,
	text_width: int,
	arrow_rect: QRect,
	gap: int
) -> HeaderPlacement:
	"""Return arrow and label rectangles for one horizontal header section."""
	if position == SortArrowPosition.EDGE:
		return HeaderPlacement(arrow_rect, label_rect)
	if position == SortArrowPosition.AFTER:
		if text_width + gap + arrow_rect.width() > label_rect.width():
			return HeaderPlacement(arrow_rect, label_rect)
		arrow = QRect(arrow_rect)
		arrow.moveLeft(min(label_rect.left() + text_width + gap, arrow_rect.left()))
		return HeaderPlacement(arrow, label_rect)
	if text_width > label_rect.width() - arrow_rect.width() - gap:
		return HeaderPlacement(arrow_rect, label_rect)
	arrow = QRect(arrow_rect)
	arrow.moveLeft(label_rect.left())
	label = QRect(label_rect)
	label.setLeft(label.left() + arrow_rect.width() + gap)
	return HeaderPlacement(arrow, label)


class HeaderSortArrow:
	"""Compute theme-aware rectangles for the header arrow and label."""

	def __init__(self, position: SortArrowPosition) -> None:
		self._position = position

	@staticmethod
	def _section_option(
		option: QStyleOptionHeader,
		widget: QHeaderView
	) -> QStyleOptionHeader:
		section_rect = QRect(
			widget.sectionViewportPosition(option.section),
			option.rect.y(),
			widget.sectionSize(option.section),
			option.rect.height()
		)
		section_option = QStyleOptionHeader(option)
		section_option.rect = section_rect
		return section_option

	def arrow_rect(
		self,
		style: QStyle,
		option: QStyleOptionHeader,
		widget: object
	) -> QRect:
		if not isinstance(widget, QHeaderView) or \
			widget.orientation() != Qt.Horizontal or \
			self._position == SortArrowPosition.EDGE:
			return option.rect
		section_option = self._section_option(option, widget)
		label_rect = widget.style().subElementRect(
			QStyle.SE_HeaderLabel, section_option, widget
		)
		arrow_rect = widget.style().subElementRect(
			QStyle.SE_HeaderArrow, section_option, widget
		)
		gap = style.pixelMetric(QStyle.PM_HeaderMargin, option, widget)
		text_width = widget.fontMetrics().horizontalAdvance(option.text)
		return place_sort_arrow(
			self._position, label_rect, text_width, arrow_rect, gap
		).arrow

	def label_rect(
		self,
		style: QStyle,
		option: QStyleOptionHeader,
		widget: object
	) -> QRect:
		if not isinstance(widget, QHeaderView) or \
			widget.orientation() != Qt.Horizontal or \
			self._position == SortArrowPosition.EDGE or \
			option.sortIndicator == QStyleOptionHeader.None_:
			return option.rect
		section_option = self._section_option(option, widget)
		arrow_rect = widget.style().subElementRect(
			QStyle.SE_HeaderArrow, section_option, widget
		)
		gap = style.pixelMetric(QStyle.PM_HeaderMargin, option, widget)
		text_width = widget.fontMetrics().horizontalAdvance(option.text)
		return place_sort_arrow(
			self._position, option.rect, text_width, arrow_rect, gap
		).label
