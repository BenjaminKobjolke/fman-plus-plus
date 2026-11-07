"""Run transfers one at a time while allowing waiting work to be reordered.

The head cannot be moved or removed because its command may already be running;
changing its position would make the visible queue disagree with the work in
flight.
"""

from collections import deque
from dataclasses import dataclass
from itertools import count
from logging import getLogger
from threading import Condition


logger = getLogger(__name__)


@dataclass(frozen=True)
class QueueEntry:
	id: int
	title: str
	running: bool


class TransferQueue:
	def __init__(self):
		self._condition = Condition()
		self._entries = []
		self._ids = count(1)
		self._listeners = []
		self._notifications = deque()
		self._notifying = False

	def run(self, title, fn):
		with self._condition:
			entry = QueueEntry(next(self._ids), title, False)
			self._entries.append(entry)
			drain_notifications = self._changed_locked()
		self._notify(drain_notifications)

		with self._condition:
			while True:
				index = self._index_of(entry.id)
				if index == -1:
					return False
				if index == 0:
					break
				self._condition.wait()

		try:
			fn()
			return True
		finally:
			with self._condition:
				index = self._index_of(entry.id)
				if index != -1:
					self._entries.pop(index)
					drain_notifications = self._changed_locked()
					self._condition.notify_all()
				else:
					drain_notifications = False
			self._notify(drain_notifications)

	def entries(self):
		with self._condition:
			return [
				QueueEntry(entry.id, entry.title, index == 0)
				for index, entry in enumerate(self._entries)
			]

	def move_up(self, entry_id):
		with self._condition:
			index = self._index_of(entry_id)
			if index <= 1:
				return False
			self._entries[index - 1], self._entries[index] = (
				self._entries[index], self._entries[index - 1])
			drain_notifications = self._changed_locked()
			self._condition.notify_all()
		self._notify(drain_notifications)
		return True

	def move_down(self, entry_id):
		with self._condition:
			index = self._index_of(entry_id)
			if index <= 0 or index >= len(self._entries) - 1:
				return False
			self._entries[index], self._entries[index + 1] = (
				self._entries[index + 1], self._entries[index])
			drain_notifications = self._changed_locked()
			self._condition.notify_all()
		self._notify(drain_notifications)
		return True

	def remove(self, entry_id):
		with self._condition:
			index = self._index_of(entry_id)
			if index <= 0:
				return False
			self._entries.pop(index)
			drain_notifications = self._changed_locked()
			self._condition.notify_all()
		self._notify(drain_notifications)
		return True

	def add_listener(self, callback):
		with self._condition:
			self._listeners.append(callback)

	def _index_of(self, entry_id):
		for index, entry in enumerate(self._entries):
			if entry.id == entry_id:
				return index
		return -1

	def _changed_locked(self):
		entries = [
			QueueEntry(entry.id, entry.title, index == 0)
			for index, entry in enumerate(self._entries)
		]
		self._notifications.append((list(self._listeners), entries))
		if self._notifying:
			return False
		self._notifying = True
		return True

	def _notify(self, drain_notifications):
		if not drain_notifications:
			return
		while True:
			with self._condition:
				if not self._notifications:
					self._notifying = False
					return
				listeners, entries = self._notifications.popleft()
			for listener in listeners:
				try:
					listener(entries)
				except Exception:
					logger.exception('Transfer queue listener failed')
