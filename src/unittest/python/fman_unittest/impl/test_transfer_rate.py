"""Tests for the transfer speed and remaining time shown in progress dialogs."""

from fman.impl.transfer_rate import TransferRate, format_rate_line
from PyQt5.QtCore import QLocale
from unittest import TestCase


class TransferRateTest(TestCase):
	def test_waits_for_one_second_of_samples(self):
		rate = TransferRate()
		rate.add(0, 0)
		rate.add(10_000_000, 0.9)
		self.assertIsNone(rate.bytes_per_second())

	def test_reports_average_rate(self):
		rate = TransferRate()
		rate.add(0, 0)
		rate.add(10_000_000, 1)
		self.assertEqual(10_000_000, rate.bytes_per_second())

	def test_drops_samples_older_than_window(self):
		rate = TransferRate()
		rate.add(0, 0)
		rate.add(10_000_000, 1.2)
		rate.add(10_000_000, 4.1)
		self.assertEqual(0, rate.bytes_per_second())
		self.assertAlmostEqual(1.2, rate._samples[0][0])

	def test_resets_samples_when_progress_goes_backwards(self):
		rate = TransferRate()
		rate.add(100, 0)
		rate.add(200, 1)
		rate.add(50, 1.1)
		self.assertIsNone(rate.bytes_per_second())

	def test_zero_rate_has_no_time_left(self):
		self.assertEqual(
			QLocale().formattedDataSize(0) + '/s',
			format_rate_line(0, 100, True)
		)

	def test_formats_estimating_rate(self):
		self.assertEqual(
			QLocale().formattedDataSize(1_000_000) + '/s · estimating',
			format_rate_line(1_000_000, 30_000_000, False)
		)

	def test_formats_time_left_in_seconds_minutes_and_hours(self):
		rate = QLocale().formattedDataSize(1_000_000) + '/s'
		self.assertEqual(rate + ' · about 30 s left',
			format_rate_line(1_000_000, 30_000_000, True))
		self.assertEqual(rate + ' · about 2 min left',
			format_rate_line(1_000_000, 120_000_000, True))
		self.assertEqual(rate + ' · about 1 h 1 min left',
			format_rate_line(1_000_000, 3_660_000_000, True))

	def test_formats_missing_rate(self):
		self.assertEqual('Calculating speed...', format_rate_line(None, 100, False))
