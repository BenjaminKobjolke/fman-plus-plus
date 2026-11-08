from unittest import TestCase

from fman.impl.quicksearch_height import fit_list_min_height


class FitListMinHeightTest(TestCase):
	def test_keeps_a_minimum_that_fits(self):
		self.assertEqual(70, fit_list_min_height(70, 0, 10))

	def test_reduces_the_minimum_by_the_overflow(self):
		self.assertEqual(55, fit_list_min_height(70, 15, 10))

	def test_keeps_one_full_row_when_overflow_exceeds_the_minimum(self):
		self.assertEqual(10, fit_list_min_height(70, 100, 10))

	def test_keeps_a_zero_minimum_at_zero(self):
		self.assertEqual(0, fit_list_min_height(0, 100, 10))
