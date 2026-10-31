"""Track when each gathered top-level item has fully transferred."""
from threading import Lock


class TransferCompletion:
	def __init__(self, on_item_done):
		self._on_item_done = on_item_done
		self._lock = Lock()
		self._current = None
		self._tasks = {}

	def begin_item(self, url):
		with self._lock:
			self._current = {
				'url': url, 'pending': 0, 'incomplete': False, 'gathered': False
			}

	def add_task(self, task):
		with self._lock:
			self._tasks[task] = self._current
			self._current['pending'] += 1

	def mark_incomplete(self):
		with self._lock:
			self._current['incomplete'] = True

	def end_item(self):
		with self._lock:
			item = self._current
			item['gathered'] = True
			self._current = None
			url = self._take_ready(item)
		if url is not None:
			self._on_item_done(url)

	def task_finished(self, task, succeeded):
		with self._lock:
			item = self._tasks.pop(task)
			item['pending'] -= 1
			if not succeeded:
				item['incomplete'] = True
			url = self._take_ready(item)
		if url is not None:
			self._on_item_done(url)

	@staticmethod
	def _take_ready(item):
		if not item['gathered'] or item['pending']:
			return None
		return None if item['incomplete'] else item['url']
