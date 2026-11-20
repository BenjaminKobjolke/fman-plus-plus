from fman.impl.view.resize_cols_to_contents import _get_ideal_column_widths, \
	_resize_column
from unittest import TestCase

class GetIdealColumnWidthsTest(TestCase):
	def test_one_column_no_change(self):
		self._expect([1], [1], [1], 1)
	def test_one_column_truncated(self):
		self._expect([2], [1], [2], 2)
	def test_one_column_too_large(self):
		self._expect([1], [2], [1], 1)
	def test_two_cols(self):
		self._expect([2, 1], [1, 2], [2, 1], 3)
	def test_truncate_first_col(self):
		self._expect([400, 100], [500, 100], [500, 100], 500, delta_percent=3)
	def test_maximize_window(self):
		self._expect([2, 1], [1, 1], [1, 1], 3)
	def test_fit_name_column_shrinks_middle_column(self):
		self._expect(
			[320, 80, 100], [100, 300, 100], [50, 80, 100], 500,
			fit_name_column=True
		)
	def test_fit_name_column_trims_name_first(self):
		self._expect(
			[70, 80, 100], [100, 300, 100], [50, 80, 100], 250,
			fit_name_column=True
		)
	def test_narrow_pane_shrinks_others_before_name(self):
		widths = _get_ideal_column_widths(
			[50, 300, 200, 200], [400, 250, 180, 190], 700,
			fit_name_column=True, min_col_width=20
		)
		self.assertAlmostEqual(400, widths[0], delta=1)
		self.assertTrue(all(width > 20 for width in widths[1:]))
		self.assertEqual(700, sum(widths))
	def test_very_narrow_pane_trims_name_after_others_at_floor(self):
		self._expect(
			[240, 20, 20, 20], [50, 300, 200, 200], [400, 250, 180, 190],
			300, fit_name_column=True, min_col_width=20
		)
	def _expect(
		self, result, widths, min_widths, available_width, delta_percent=0,
		fit_name_column=False, min_col_width=0
	):
		actual = \
			_get_ideal_column_widths(
				widths, min_widths, available_width, fit_name_column, min_col_width
			)
		self.assertEqual(len(result), len(actual))
		if delta_percent:
			for r, a in zip(result, actual):
				if delta_percent:
					delta = int(r * delta_percent / 100)
					self.assertLessEqual(r - delta, a)
					self.assertGreaterEqual(r + delta, a)
		else:
			self.assertEqual(result, actual)

class ResizeColumnTest(TestCase):
	def test_enlarge(self):
		self._expect([2, 1, 1], 0, 2, [1, 2, 1], [1, 1, 1])
	def test_shrink(self):
		self._expect([1, 2, 1], 0, 1, [2, 1, 1], [1, 1, 1])
	def test_shrink_below_available_width(self):
		self._expect([1, 1, 2], 0, 1, [2, 1, 2], [1, 1, 2], 4)
	def test_shrink_last_but_one(self):
		self._expect([1, 1, 2], 1, 1, [1, 2, 1], [2, 1, 2])
	def test_enlarge_trims_last_col(self):
		self._expect([2, 1], 0, 2, [1, 2], [1, 1], 3)
	def test_enlarge_never_exceeds_available_width(self):
		self._expect([5, 3, 3], 0, 8, [5, 3, 3], [1, 3, 3], 11)
	def test_enlarge_partly_trims_then_clamps(self):
		self._expect([6, 3, 3], 0, 8, [5, 4, 3], [1, 3, 3], 12)
	def test_rightalign_last_col(self):
		self._expect([1, 2, 1], 0, 1, [2, 1, 1], [1, 1, 1])
	def _expect(
		self, result, col, old_size, widths, min_widths, available_width=None
	):
		if available_width is None:
			available_width = sum(widths)
		actual = _resize_column(
			col, old_size, widths, min_widths, available_width
		)
		self.assertEqual(result, actual)
