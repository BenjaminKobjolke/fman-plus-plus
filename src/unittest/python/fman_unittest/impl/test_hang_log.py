"""HangLog writes all thread stacks once per GUI-thread stall."""

from fman.impl.hang_log import HangLog, STALL_SECONDS
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase


class HangLogTest(TestCase):
	def setUp(self):
		self._now = 100.0
		temp_dir = TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self._path = join(temp_dir.name, 'Hangs.log')
		self._hang_log = HangLog(self._path, clock=lambda: self._now)
		self._hang_log.beat()
	def test_no_entry_without_stall(self):
		self._now += STALL_SECONDS - 1
		self._hang_log.check_stall()
		self.assertEqual('', self._read())
	def test_stale_heartbeat_logs_thread_stacks_once(self):
		self._now += STALL_SECONDS + 1
		self._hang_log.check_stall()
		first = self._read()
		self.assertIn('GUI thread stalled', first)
		self.assertIn('test_stale_heartbeat_logs_thread_stacks_once', first)
		self._now += 1
		self._hang_log.check_stall()
		self.assertEqual(first, self._read())
	def test_fresh_heartbeat_logs_end_and_rearms(self):
		self._now += STALL_SECONDS + 1
		self._hang_log.check_stall()
		self._hang_log.beat()
		self._hang_log.check_stall()
		self.assertIn('GUI thread responsive again', self._read())
		self._now += STALL_SECONDS + 1
		self._hang_log.check_stall()
		self.assertEqual(2, self._read().count('GUI thread stalled'))
	def _read(self):
		try:
			with open(self._path, encoding='utf-8') as log_file:
				return log_file.read()
		except FileNotFoundError:
			return ''
