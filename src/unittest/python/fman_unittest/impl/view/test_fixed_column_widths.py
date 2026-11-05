from fman.impl.view.fixed_column_widths import get_target_widths
from unittest import TestCase


class GetTargetWidthsTest(TestCase):
	def test_auto_fit_uses_content_hints(self):
		self.assertEqual(
			[240, 70, 110],
			get_target_widths(
				['Name', 'Size', 'Modified'], [240, 70, 110], [40, 50, 60],
				{'Size': 140, 'Modified': 180}, {}, fixed=False
			)
		)

	def test_fixed_columns_prefer_dragged_then_sample_then_content(self):
		self.assertEqual(
			[240, 95, 110],
			get_target_widths(
				['Name', 'Size', 'Modified'], [240, 70, 110], [40, 50, 60],
				{'Size': 140},
				{'Size': 95}, fixed=True
			)
		)

	def test_fixed_widths_keep_the_header_minimum(self):
		self.assertEqual(
			[240, 40, 50],
			get_target_widths(
				['Name', 'Size', 'Modified'], [240, 300, 400], [240, 40, 50],
				{'Size': 40, 'Modified': 50},
				{'Size': 30, 'Modified': 20}, fixed=True
			)
		)

	def test_name_always_uses_its_content_hint(self):
		self.assertEqual(
			[240, 300],
			get_target_widths(
				['Name', 'Size'], [240, 70], [40, 50],
				{'Name': 500, 'Size': 140}, {'Name': 100, 'Size': 300},
				fixed=True
			)
		)
