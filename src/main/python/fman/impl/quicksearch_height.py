"""Height calculations for fitting quicksearch lists inside their parent."""


def fit_list_min_height(min_height: int, overflow: int, row_height: int) -> int:
	"""Reduce a list minimum to fit, keeping one full row when nonzero."""
	if min_height == 0:
		return 0
	return max(row_height, min_height - overflow)
