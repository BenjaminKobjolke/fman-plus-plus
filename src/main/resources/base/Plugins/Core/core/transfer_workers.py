"""
Runs the tasks a FileTreeOperation gathers on one or more worker threads. Slow
per-file transports (FTP) gain from several. The progress dialog polls
snapshot() and calls add() / remove() while the workers run.
It also polls connection_count() for the transfer dialog's connection label.
"""
from dataclasses import dataclass, replace
from fman.impl.task import ChildProgressDialog
from threading import Condition, Thread

# Ends the queue of tasks. It stays in the queue so every worker sees it.
DONE = object()

_MAX_WORKERS = 10

@dataclass
class WorkerState:
	id: int
	title: str = ''
	progress: int = 0
	size: int = 0
	retiring: bool = False

class TransferWorkers:
	def __init__(
		self, count, queue, run_task, should_stop=lambda: False,
		connection_count=lambda: None
	):
		"""
		run_task(worker, task, is_last) runs one task and returns False to
		stop all workers. should_stop() is checked before each task.
		connection_count() returns the current count shown beside the thread
		count, or None when it is unknown.
		"""
		self._count = count
		self._queue = queue
		self._run_task = run_task
		self._should_stop = should_stop
		self._connection_count = connection_count
		self._lock = Condition()
		# Ticket -> whether later tasks wait for it. Holds the tasks taken off
		# the queue that have not ended yet. See Task#waits_for_earlier_tasks.
		self._unfinished = {}
		self._next_ticket = 1
		self._workers = []
		self._threads = []
		self._next_id = 1
		self._aborted = False
		self._finished = False
		self._error = None
	def start(self):
		if self._count == 1:
			# Runs to the end right here: no worker view is shown, so nothing
			# can add() a second worker.
			with self._lock:
				worker = self._new_worker()
			self._work(worker)
		else:
			for _ in range(self._count):
				self.add()
	def join(self):
		while True:
			with self._lock:
				threads = [t for t in self._threads if t.is_alive()]
				if not threads:
					self._finished = True
					break
			# Workers added meanwhile are picked up by the next round.
			for thread in threads:
				thread.join()
		if self._error is not None:
			raise self._error
	def can_add(self):
		with self._lock:
			return self._can_add()
	def add(self):
		with self._lock:
			if not self._can_add():
				return
			worker = self._new_worker()
			thread = Thread(target=self._work, args=(worker,), daemon=True)
			self._threads.append(thread)
			thread.start()
	def can_remove(self):
		with self._lock:
			return self._can_remove()
	def remove(self):
		# The worker finishes its active task first. One blocked waiting for
		# a task runs the one it gets, then stops.
		with self._lock:
			if self._can_remove():
				self._active_workers()[-1].retiring = True
	def snapshot(self):
		with self._lock:
			return [replace(worker) for worker in self._workers]
	def counts(self):
		"""
		(done, total) tasks. The total grows while the gatherer still queues.
		"""
		# ponytail: counts every task, so Move's "Postprocessing <dir>" too.
		# Filter by task type if the count should hold files only.
		queue = self._queue
		# The queue's lock first, like _take(...), so the two cannot deadlock.
		with queue.not_empty:
			queued = sum(1 for task in queue.queue if task is not DONE)
			with self._lock:
				taken = self._next_ticket - 1
				return taken - len(self._unfinished), taken + queued
	def connection_count(self):
		return self._connection_count()
	def _can_add(self):
		return not (self._finished or self._aborted) and \
			len(self._workers) < _MAX_WORKERS
	def _can_remove(self):
		# At least one worker always stays.
		return len(self._active_workers()) > 1
	def _active_workers(self):
		return [w for w in self._workers if not w.retiring]
	def _new_worker(self):
		result = WorkerState(self._next_id)
		self._next_id += 1
		self._workers.append(result)
		return result
	def _work(self, worker):
		ticket = None
		try:
			while not (self._aborted or worker.retiring):
				task, ticket = self._take()
				if task is DONE:
					break
				is_last = self._next_is_done()
				self._wait_for_turn(task, ticket)
				if self._aborted or self._should_stop():
					break
				if not self._run_task(worker, task, is_last):
					self._aborted = True
				self._finish(ticket)
				ticket = None
		except BaseException as e:
			self._aborted = True
			with self._lock:
				if self._error is None:
					self._error = e
		finally:
			if ticket is not None:
				self._finish(ticket)
			with self._lock:
				self._workers.remove(worker)
	def _take(self):
		# Numbered while the queue is still locked, so the numbers follow the
		# queue's order however the workers race for it.
		queue = self._queue
		with queue.not_empty:
			if self._first_queued() is DONE:
				# Left in the queue for the other workers.
				return DONE, None
			task = queue.queue.popleft()
			with self._lock:
				ticket = self._next_ticket
				self._next_ticket += 1
				self._unfinished[ticket] = \
					_waits_for_earlier(task) or \
					getattr(task, 'blocks_later_tasks', False)
		return task, ticket
	def _wait_for_turn(self, task, ticket):
		waits = _waits_for_earlier(task)
		with self._lock:
			while any(
				earlier < ticket and (waits or blocks)
				for earlier, blocks in self._unfinished.items()
			):
				self._lock.wait()
	def _finish(self, ticket):
		with self._lock:
			del self._unfinished[ticket]
			self._lock.notify_all()
	def _next_is_done(self):
		# Waits for the next task like a look-ahead, but does not take it: it
		# may become another worker's.
		with self._queue.not_empty:
			return self._first_queued() is DONE
	def _first_queued(self):
		# Call holding the queue's lock. Waits until the queue holds an item,
		# without taking it: Queue has no public peek. put(...) wakes only one
		# waiter, so pass the wakeup on, or another waiting worker sleeps
		# forever.
		queue = self._queue
		while not queue.queue:
			queue.not_empty.wait()
		queue.not_empty.notify()
		return queue.queue[0]

def _waits_for_earlier(task):
	# Plain objects without Task's flags are fine too, e.g. in tests.
	return getattr(task, 'waits_for_earlier_tasks', False)

class WorkerProgress(ChildProgressDialog):
	"""
	The dialog of a task a worker runs. ChildProgressDialog sets the parent's
	progress absolutely, so tasks running in parallel would overwrite each
	other. This one adds the change instead.
	"""
	def __init__(self, parent, lock, worker, task, forward_text):
		super().__init__(parent)
		self._lock = lock
		self._worker = worker
		self._forward_text = forward_text
		self._done = 0
		worker.size = task.get_size()
		worker.progress = 0
		self.set_text(task.get_title())
	def set_text(self, status):
		self._worker.title = status
		if self._forward_text:
			super().set_text(status)
	def set_progress(self, progress):
		with self._lock:
			self._parent.set_progress(
				self._parent.get_progress() + progress - self._done
			)
			self._done = progress
		self._worker.progress = progress
	def get_progress(self):
		return self._done
