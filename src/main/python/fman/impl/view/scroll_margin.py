"""Keep N rows between the cursor and list edges, like vim's scrolloff (#186)."""

from PyQt5.QtWidgets import QAbstractItemView

from fman.impl.view.uniform_row_heights import UniformRowHeights


class ScrollMargin(UniformRowHeights):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._scroll_margin = 0

	def set_scroll_margin(self, rows: int) -> None:
		self._scroll_margin = rows

	def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
		if hint != self.EnsureVisible or not index.isValid() or not self._scroll_margin:
			super().scrollTo(index, hint)
			return

		row_height = self.get_row_height()
		viewport_height = self.viewport().height()
		if row_height <= 0 or viewport_height <= 0:
			super().scrollTo(index, hint)
			return

		fully_visible_rows = viewport_height // row_height
		margin = min(self._scroll_margin, max(0, (fully_visible_rows - 1) // 2))
		if margin == 0:
			super().scrollTo(index, hint)
			return
		if self._scroll_margin >= fully_visible_rows // 2:
			super().scrollTo(index, self.PositionAtCenter)
			return

		row_count = self.model().rowCount()
		first_row = max(index.row() - margin, 0)
		last_row = min(index.row() + margin, row_count - 1)
		# Since 2 × margin + 1 rows fit, ensuring the bottom target
		# cannot push the top target out.
		super().scrollTo(index.sibling(first_row, index.column()), self.EnsureVisible)
		super().scrollTo(index.sibling(last_row, index.column()), self.EnsureVisible)
