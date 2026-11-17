from core.natural_sort import natural_key
from unittest import TestCase


class NaturalSortTest(TestCase):
	def test_long_numeric_runs_sort_by_value(self):
		self.assertLess(natural_key('file999999'), natural_key('file1000000'))
	def test_short_numeric_runs_sort_by_value(self):
		self.assertLess(natural_key('file2'), natural_key('file10'))
	def test_equal_numeric_values_keep_input_order(self):
		names = ['a01', 'a1']
		self.assertEqual(names, sorted(names, key=natural_key))
	def test_unicode_decimal_digits_sort_like_ascii_digits(self):
		self.assertEqual(natural_key('x2'), natural_key('x٢'))
	def test_sort_is_case_insensitive(self):
		self.assertEqual(natural_key('FILE2'), natural_key('file2'))
