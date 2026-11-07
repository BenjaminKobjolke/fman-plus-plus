from fman.impl.transfer_queue import TransferQueue
from threading import Event, Thread
from unittest import TestCase


class TransferQueueTest(TestCase):
	def setUp(self):
		self.queue = TransferQueue()

	def test_runs_immediately_when_queue_is_empty(self):
		results = []

		run = self.queue.run('First transfer', lambda: results.append('ran'))

		self.assertTrue(run)
		self.assertEqual(['ran'], results)
		self.assertEqual([], self.queue.entries())

	def test_waits_for_the_current_transfer(self):
		first_started = Event()
		release_first = Event()
		second_started = Event()
		first_thread = Thread(target=lambda: self.queue.run(
			'First transfer', lambda: self._run_blocking(first_started, release_first)))
		second_thread = Thread(target=lambda: self.queue.run(
			'Second transfer', second_started.set))
		first_thread.start()
		self.assertTrue(first_started.wait(2))
		second_thread.start()
		self._wait_for_entry_count(2)

		self.assertFalse(second_started.is_set())
		release_first.set()
		first_thread.join(2)
		second_thread.join(2)

		self.assertFalse(first_thread.is_alive())
		self.assertFalse(second_thread.is_alive())
		self.assertTrue(second_started.is_set())

	def test_moves_and_removes_waiting_transfers(self):
		first_started = Event()
		release_first = Event()
		started = []
		first_thread = Thread(target=lambda: self.queue.run(
			'First', lambda: self._run_blocking(first_started, release_first)))
		first_thread.start()
		self.assertTrue(first_started.wait(2))

		second_result = []
		third_result = []
		second_thread = Thread(target=lambda: second_result.append(
			self.queue.run('Second', lambda: started.append('Second'))))
		third_thread = Thread(target=lambda: third_result.append(
			self.queue.run('Third', lambda: started.append('Third'))))
		second_thread.start()
		self._wait_for_entry_count(2)
		third_thread.start()
		self._wait_for_entry_count(3)
		entries = self.queue.entries()
		second_id, third_id = entries[1].id, entries[2].id

		self.assertTrue(self.queue.move_down(second_id))
		self.assertEqual(['First', 'Third', 'Second'],
			[entry.title for entry in self.queue.entries()])
		self.assertTrue(self.queue.move_up(second_id))
		self.assertEqual(['First', 'Second', 'Third'],
			[entry.title for entry in self.queue.entries()])
		self.assertTrue(self.queue.remove(third_id))
		self.assertFalse(self.queue.remove(third_id))

		release_first.set()
		first_thread.join(2)
		second_thread.join(2)
		third_thread.join(2)

		self.assertEqual(['Second'], started)
		self.assertEqual([True], second_result)
		self.assertEqual([False], third_result)
		self.assertFalse(any(thread.is_alive() for thread in (
			first_thread, second_thread, third_thread)))

	def test_running_entry_cannot_be_moved_or_removed(self):
		first_started = Event()
		release_first = Event()
		first_thread = Thread(target=lambda: self.queue.run(
			'First', lambda: self._run_blocking(first_started, release_first)))
		first_thread.start()
		self.assertTrue(first_started.wait(2))
		waiting_result = []
		waiting_thread = Thread(target=lambda: waiting_result.append(
			self.queue.run('Waiting', lambda: None)))
		waiting_thread.start()
		self._wait_for_entry_count(2)
		first_id = self.queue.entries()[0].id

		self.assertFalse(self.queue.move_up(first_id))
		self.assertFalse(self.queue.move_down(first_id))
		self.assertFalse(self.queue.remove(first_id))
		self.assertEqual(['First', 'Waiting'],
			[entry.title for entry in self.queue.entries()])

		release_first.set()
		first_thread.join(2)
		waiting_thread.join(2)
		self.assertEqual([True], waiting_result)

	def test_only_head_entry_reports_running(self):
		first_started = Event()
		release_first = Event()
		first_thread = Thread(target=lambda: self.queue.run(
			'First', lambda: self._run_blocking(first_started, release_first)))
		first_thread.start()
		self.assertTrue(first_started.wait(2))
		second_thread = Thread(target=lambda: self.queue.run('Second', lambda: None))
		third_thread = Thread(target=lambda: self.queue.run('Third', lambda: None))
		second_thread.start()
		self._wait_for_entry_count(2)
		third_thread.start()
		self._wait_for_entry_count(3)

		self.assertEqual([True, False, False],
			[entry.running for entry in self.queue.entries()])
		release_first.set()
		first_thread.join(2)
		second_thread.join(2)
		third_thread.join(2)

	def test_exception_propagates_and_next_transfer_starts(self):
		first_started = Event()
		release_first = Event()
		first_errors = []
		second_started = Event()
		failure = ValueError('transfer failed')

		def first_transfer():
			self._run_blocking(first_started, release_first)
			raise failure

		def run_first():
			try:
				self.queue.run('First', first_transfer)
			except Exception as error:
				first_errors.append(error)

		first_thread = Thread(target=run_first)
		first_thread.start()
		self.assertTrue(first_started.wait(2))
		second_thread = Thread(target=lambda: self.queue.run(
			'Second', second_started.set))
		second_thread.start()
		self._wait_for_entry_count(2)
		release_first.set()
		first_thread.join(2)
		second_thread.join(2)

		self.assertEqual([failure], first_errors)
		self.assertTrue(second_started.is_set())
		self.assertFalse(first_thread.is_alive())
		self.assertFalse(second_thread.is_alive())

	def test_listeners_run_after_each_queue_change(self):
		changes = []

		def listener(entries):
			changes.append(tuple((entry.title, entry.running) for entry in entries))

		self.queue.add_listener(listener)
		self.assertTrue(self.queue.run('First', lambda: None))

		self.assertEqual([
			(('First', True),),
			(),
		], changes)

	def test_listener_notifications_are_delivered_in_queue_change_order(self):
		first_notification_started = Event()
		release_first_notification = Event()
		second_notification_started = Event()
		changes = []

		def listener(entries):
			titles = tuple(entry.title for entry in entries)
			if titles == ('First',):
				first_notification_started.set()
				if not release_first_notification.wait(2):
					self.fail('Timed out waiting to release the first notification')
			elif titles == ('First', 'Second'):
				second_notification_started.set()
			changes.append(titles)

		self.queue.add_listener(listener)
		first_thread = Thread(target=lambda: self.queue.run('First', lambda: None))
		first_thread.start()
		self.assertTrue(first_notification_started.wait(2))
		second_thread = Thread(target=lambda: self.queue.run('Second', lambda: None))
		second_thread.start()
		self._wait_for_entry_count(2)

		self.assertFalse(second_notification_started.is_set())
		release_first_notification.set()
		first_thread.join(2)
		second_thread.join(2)

		self.assertFalse(first_thread.is_alive())
		self.assertFalse(second_thread.is_alive())
		self.assertLess(changes.index(('First',)), changes.index(('First', 'Second')))

	def _run_blocking(self, started, release):
		started.set()
		if not release.wait(2):
			self.fail('Timed out waiting to release the running transfer')

	def _wait_for_entry_count(self, expected):
		changed = Event()
		self.queue.add_listener(lambda entries: changed.set()
			if len(entries) >= expected else None)
		if len(self.queue.entries()) < expected:
			self.assertTrue(changed.wait(2))
		self.assertGreaterEqual(len(self.queue.entries()), expected)
