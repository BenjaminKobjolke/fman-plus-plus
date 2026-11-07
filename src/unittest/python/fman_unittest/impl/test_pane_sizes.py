"""Conversions between pane size weights, percentages and splitter pixels."""

from fman.impl.pane_sizes import to_percentages, to_pixels, validate_sizes
from unittest import TestCase


class PaneSizeConversionTest(TestCase):
	def test_to_percentages_converts_widths(self):
		self.assertEqual([75.0, 25.0], to_percentages([300, 100]))

	def test_to_percentages_preserves_hidden_panes(self):
		self.assertEqual([0.0, 100.0], to_percentages([0, 400]))

	def test_to_percentages_uses_equal_shares_when_all_widths_are_zero(self):
		self.assertEqual([50.0, 50.0], to_percentages([0, 0]))
		self.assertEqual([], to_percentages([]))

	def test_to_pixels_converts_percentages_and_relative_weights(self):
		self.assertEqual([300, 100], to_pixels([75, 25], 400))
		self.assertEqual([100, 100, 100], to_pixels([1, 1, 1], 300))
		self.assertEqual([150, 250], to_pixels([1.5, 2.5], 400))

	def test_validate_sizes_requires_one_value_per_pane(self):
		with self.assertRaisesRegex(ValueError, 'Expected 3 pane sizes.*got 2'):
			validate_sizes([1, 2], 3)

	def test_validate_sizes_requires_positive_numbers(self):
		for sizes in ([0, 1], [-1, 2]):
			with self.subTest(sizes=sizes):
				with self.assertRaisesRegex(ValueError, 'positive numbers'):
					validate_sizes(sizes, 2)

	def test_validate_sizes_rejects_strings_and_booleans(self):
		for sizes in (['a', 1], [True, 1]):
			with self.subTest(sizes=sizes):
				with self.assertRaisesRegex(ValueError, 'positive numbers'):
					validate_sizes(sizes, 2)

	def test_validate_sizes_accepts_positive_integers_and_floats(self):
		self.assertEqual([75.0, 25.0], validate_sizes([75, 25], 2))
		self.assertEqual([1.5, 2.5], validate_sizes([1.5, 2.5], 2))
