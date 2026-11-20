"""Sample byte progress and format a transfer speed line."""

from collections import deque
from math import ceil
from PyQt5.QtCore import QLocale

_CALCULATING_SPEED = 'Calculating speed...'
_RATE_PER_SECOND = '%s/s'
_ESTIMATING = ' · estimating'
_ABOUT = ' · about %s left'
_SECONDS_LEFT = '%s s'
_MINUTES_LEFT = '%s min'
_HOURS_LEFT = '%s h %s min'


class TransferRate:
	WINDOW_SECONDS = 3
	MIN_SPAN_SECONDS = 1

	def __init__(self):
		self._samples = deque()

	def add(self, progress, now):
		if self._samples and progress < self._samples[-1][1]:
			self._samples.clear()
		self._samples.append((now, progress))
		cutoff = now - self.WINDOW_SECONDS
		while len(self._samples) > 1 and self._samples[0][0] < cutoff:
			self._samples.popleft()

	def bytes_per_second(self):
		if len(self._samples) < 2:
			return None
		first_time, first_progress = self._samples[0]
		last_time, last_progress = self._samples[-1]
		span = last_time - first_time
		if span < self.MIN_SPAN_SECONDS:
			return None
		return (last_progress - first_progress) / span


def format_rate_line(rate, remaining, size_final):
	if rate is None:
		return _CALCULATING_SPEED
	rate_text = _RATE_PER_SECOND % QLocale().formattedDataSize(int(rate))
	if rate <= 0:
		return rate_text
	if not size_final:
		return rate_text + _ESTIMATING
	return rate_text + (_ABOUT % _format_duration(remaining / rate))


def _format_duration(seconds):
	seconds = ceil(seconds)
	if seconds < 60:
		return _SECONDS_LEFT % seconds
	minutes = ceil(seconds / 60)
	if minutes < 60:
		return _MINUTES_LEFT % minutes
	hours, minutes = divmod(minutes, 60)
	return _HOURS_LEFT % (hours, minutes)
