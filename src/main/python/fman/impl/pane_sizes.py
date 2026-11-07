"""Convert relative pane sizes to percentages and QSplitter pixel widths."""

from numbers import Real
from typing import Sequence


def validate_sizes(sizes: Sequence[Real], pane_count: int) -> list[float]:
	if len(sizes) != pane_count:
		raise ValueError(
			'Expected %d pane sizes, one per pane, got %d.' %
			(pane_count, len(sizes))
		)
	if any(
		isinstance(size, bool) or not isinstance(size, Real) or size <= 0
		for size in sizes
	):
		raise ValueError('Pane sizes must be positive numbers.')
	return [float(size) for size in sizes]


def to_pixels(sizes: Sequence[float], total: int) -> list[int]:
	total_size = sum(sizes)
	if not total_size:
		return [0 for _ in sizes]
	return [round(size * total / total_size) for size in sizes]


def to_percentages(widths: Sequence[int]) -> list[float]:
	total_width = sum(widths)
	if not total_width:
		return [100.0 / len(widths) for _ in widths] if widths else []
	return [100.0 * width / total_width for width in widths]
