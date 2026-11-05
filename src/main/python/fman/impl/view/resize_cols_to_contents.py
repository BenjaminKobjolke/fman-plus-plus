from fman.impl.view.uniform_row_heights import UniformRowHeights
from fman.impl.view.fixed_column_widths import get_target_widths
from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtWidgets import QApplication, QStyle, QStyleOptionViewItem
from math import ceil

class ResizeColumnsToContents(UniformRowHeights):
	def __init__(self, parent):
		super().__init__(parent)
		self.horizontalHeader().sectionResized.connect(self._on_col_resized)
		self._old_col_widths = None
		self._dragged_widths = {}
		self._column_widths_by_name = {}
		self._handle_col_resize = True
		self.fit_name_column = True
		self._restore_widths_pending = False
		self._resize_timer = QTimer(self)
		self._resize_timer.setSingleShot(True)
		self._resize_timer.timeout.connect(self._on_resize_timer)
	def resizeColumnsToContents(self):
		self._resize_cols_to_contents()
	def resizeEvent(self, event):
		super().resizeEvent(event)
		num_rows_visible = self._get_num_visible_rows()
		self.model().set_num_rows_to_preload(num_rows_visible)
		# Performance improvement: We call sizeHintForColumn(...). By default,
		# this considers 1000 rows. So what Qt does is that it "loads" the 1000
		# rows and then computes their size. This can be expensive. We therefore
		# reduce 1000 to the number of rows that are actually visible (typically
		# ~50).
		self.horizontalHeader().setResizeContentsPrecision(num_rows_visible)
		self._resize_cols_to_contents(self._old_col_widths)
		self._old_col_widths = self._get_column_widths()
	def _get_num_visible_rows(self):
		row_height = self.get_row_height()
		if row_height == -1:
			# This for instance happens when the model has 0 rows.
			return 0
		content_height = self.height() - self.horizontalHeader().height()
		# Assumes all rows have the same height:
		return ceil(content_height / row_height)
	def setModel(self, model):
		old_model = self.model()
		if old_model:
			old_model.modelReset.disconnect(self._on_model_reset)
			old_model.modelAboutToBeReset.disconnect(
				self._on_model_about_to_reset
			)
			old_model.rowsInserted.disconnect(self._on_rows_inserted)
		super().setModel(model)
		model.modelAboutToBeReset.connect(self._on_model_about_to_reset)
		model.modelReset.connect(self._on_model_reset)
		model.rowsInserted.connect(self._on_rows_inserted)
		if self._column_widths_by_name:
			self._restore_widths_pending = True
			self._resize_timer.start(0)
	def _on_model_about_to_reset(self):
		self._record_column_widths()
	def _on_model_reset(self):
		self._restore_widths_pending = True
		self._resize_timer.start(0)
	def _on_rows_inserted(self, *_):
		self._resize_timer.start(0)
	def _on_resize_timer(self):
		if self._restore_widths_pending:
			self._restore_column_widths()
			self._restore_widths_pending = False
		self._resize_cols_to_contents()
	def _record_column_widths(self):
		model = self.model()
		if model is not None and hasattr(model, 'get_columns'):
			self._column_widths_by_name.update({
				column.get_qualified_name(): self.columnWidth(i)
				for i, column in enumerate(model.get_columns())
				if i < self._num_columns
			})
	def _restore_column_widths(self):
		self._handle_col_resize = False
		try:
			for i, column in enumerate(self.model().get_columns()):
				name = column.get_qualified_name()
				if i < self._num_columns and name in self._column_widths_by_name:
					self.setColumnWidth(i, self._column_widths_by_name[name])
		finally:
			self._handle_col_resize = True
		self._record_column_widths()
	def get_dragged_widths(self):
		return dict(self._dragged_widths)
	def set_dragged_widths(self, widths):
		self._dragged_widths = {
			name: width for name, width in widths.items()
			if isinstance(name, str) and type(width) is int
		} if isinstance(widths, dict) else {}
	def _resize_cols_to_contents(self, curr_widths=None):
		visible_columns = self._get_visible_columns()
		if not visible_columns:
			return
		if self._get_rows_visible_but_not_loaded():
			return
		if curr_widths is None or len(curr_widths) != self._num_columns:
			curr_widths = self._get_column_widths()
		visible_curr_widths = [curr_widths[c] for c in visible_columns]
		header = self.horizontalHeader()
		content_hints = [self.sizeHintForColumn(c) for c in visible_columns]
		header_hints = [header.sectionSizeHint(c) for c in visible_columns]
		target_widths = self._get_target_widths(
			visible_columns, content_hints, header_hints, self._dragged_widths
		)
		width = self._get_width_excl_scrollbar()
		columns = self.model().get_columns()
		name_index = next(
			(i for i, c in enumerate(visible_columns)
			if columns[c].get_qualified_name().split('.')[-1] == 'Name'), 0
		)
		fixed_width = sum(
			w for i, w in enumerate(target_widths) if i != name_index
		)
		if not self.fit_name_column and fixed_width <= width:
			ideal_widths = list(target_widths)
			ideal_widths[name_index] = width - fixed_width
		else:
			if not self.fit_name_column:
				visible_curr_widths = target_widths
			ideal_widths = _get_ideal_column_widths(
				visible_curr_widths, target_widths, width, self.fit_name_column
			)
		self._handle_col_resize = False
		try:
			for col, col_width in zip(visible_columns, ideal_widths):
				self.setColumnWidth(col, col_width)
		finally:
			self._handle_col_resize = True
		self._record_column_widths()
	def _get_target_widths(
		self, visible_columns, content_hints, header_hints, dragged
	):
		columns = self.model().get_columns()
		names = [columns[c].get_qualified_name() for c in visible_columns]
		samples = {
			column.get_qualified_name(): measure_text_width(
				self, column.get_widest_str()
			)
			for c, column in enumerate(columns)
			if c in visible_columns and column.get_widest_str()
		}
		return get_target_widths(
			names, content_hints, header_hints, samples, dragged,
			fixed=not self.fit_name_column
		)
	def _get_rows_visible_but_not_loaded(self):
		model = self.model()
		return [
			i for i in self.get_visible_row_range()
			if not model.row_is_loaded(i)
		]
	def _get_width_excl_scrollbar(self):
		return self.width() - self.verticalScrollBar().sizeHint().width()
	def _get_column_widths(self):
		return [self.columnWidth(i) for i in range(self._num_columns)]
	def _get_visible_columns(self):
		return [c for c in range(self._num_columns) if not self.isColumnHidden(c)]
	@property
	def _num_columns(self):
		return self.horizontalHeader().count()
	def _on_col_resized(self, col, old_size, size):
		if old_size == size:
			return
		model = self.model()
		if not hasattr(model, 'get_columns'):
			return
		visible_columns = self._get_visible_columns()
		if col not in visible_columns:
			return
		# Prevent infinite recursion:
		if not self._handle_col_resize:
			return
		self._handle_col_resize = False
		try:
			visible_index = visible_columns.index(col)
			widths = [self.columnWidth(c) for c in visible_columns]
			widths[visible_index] = old_size
			header = self.horizontalHeader()
			content_hints = [self.sizeHintForColumn(c) for c in visible_columns]
			header_hints = [header.sectionSizeHint(c) for c in visible_columns]
			columns = self.model().get_columns()
			dragging = bool(QApplication.mouseButtons())
			dragged = dict(self._dragged_widths)
			if dragging:
				dragged.pop(columns[col].get_qualified_name(), None)
			min_widths = self._get_target_widths(
				visible_columns, content_hints, header_hints, dragged
			)
			width = self._get_width_excl_scrollbar()
			new_widths = _resize_column(visible_index, size, widths, min_widths, width)
			for visible_col, col_width in zip(visible_columns, new_widths):
				self.setColumnWidth(visible_col, col_width)
			if dragging:
				column = self.model().get_columns()[col]
				self._dragged_widths[column.get_qualified_name()] = \
					self.columnWidth(col)
			self._record_column_widths()
		finally:
			self._handle_col_resize = True


def measure_text_width(view, text):
	option = QStyleOptionViewItem(view.viewOptions())
	option.text = text
	option.features |= QStyleOptionViewItem.HasDisplay
	text_size = QSize(view.fontMetrics().horizontalAdvance(text), 0)
	return view.style().sizeFromContents(
		QStyle.CT_ItemViewItem, option, text_size, view
	).width()


def _get_ideal_column_widths(
	curr_widths, min_widths, available_width, fit_name_column=False
):
	if not min_widths:
		raise ValueError(repr(min_widths))
	if len(curr_widths) != len(min_widths):
		curr_widths = [0] * len(min_widths)
	if fit_name_column:
		curr_widths = [curr_widths[0]] + min_widths[1:]
	result = list(curr_widths)
	width = sum(curr_widths)
	min_width = sum(min_widths)
	truncated_columns = [
		c for c, (w, m_w) in enumerate(zip(curr_widths, min_widths))
		if w < m_w
	]
	if truncated_columns:
		if min_width <= available_width:
			# Simply enlarge the truncated columns.
			for c in truncated_columns:
				result[c] = min_widths[c]
			width = sum(result)
	if width > available_width:
		trim_required = width - available_width
		trimmable_cols = [
			c for c, (w, m_w) in enumerate(zip(result, min_widths))
			if w > m_w
		]
		trimmable_widths = [result[c] - min_widths[c] for c in trimmable_cols]
		trimmable_width = sum(trimmable_widths)
		to_trim = min(trim_required, trimmable_width)
		col_trims = _distribute_evenly(to_trim, trimmable_widths)
		for c, trim in zip(trimmable_cols, col_trims):
			result[c] -= trim
		trim_required -= to_trim
		if trim_required > 0:
			col_trims = _distribute_exponentially(trim_required, result)
			for c, trim in enumerate(col_trims):
				result[c] -= trim
	elif width < available_width:
		result[0] += available_width - width
	last_col_excess = result[-1] - min_widths[-1]
	if last_col_excess > 0:
		result[-1] -= last_col_excess
		result[0] += last_col_excess
	return result


def _distribute_evenly(width, proportions):
	total = sum(proportions)
	if not total:
		return [0] * len(proportions)
	return [int(p / total * width) for p in proportions]


def _distribute_exponentially(width, proportions):
	total = sum(p * p for p in proportions)
	if not total:
		return [0] * len(proportions)
	return [int(p * p / total * width) for p in proportions]


def _resize_column(col, new_size, widths, min_widths, available_width):
	old_size = widths[col]
	result = list(widths)
	result[col] = new_size
	if old_size <= 0 or col == len(widths) - 1:
		return result
	delta = new_size - old_size
	if delta > 0:
		for c in range(col + 1, len(widths)):
			width = widths[c]
			trimmable = width - min_widths[c]
			if trimmable > 0:
				trim = min(delta, trimmable)
				result[c] = width - trim
				delta -= trim
				if not delta:
					break
		overflow = sum(result) - available_width
		if overflow > 0:
			result[col] -= min(overflow, result[col] - min_widths[col])
	else:
		next_col = col + 1
		if sum(result) < available_width:
			result[next_col] -= delta
	to_distribute = available_width - sum(result)
	if to_distribute > 0:
		for c, (w, m_w) in enumerate(zip(widths, min_widths)):
			room = m_w - w
			if room > 0:
				expand = min(to_distribute, room)
				result[c] += expand
				to_distribute -= expand
				if not to_distribute:
					break
	return result
