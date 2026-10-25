"""Keep successful, undoable file operations for the current fman session."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrashRecord:
	urls: tuple


@dataclass(frozen=True)
class RenameRecord:
	urls: tuple


@dataclass(frozen=True)
class CopyRecord:
	urls: tuple


@dataclass(frozen=True)
class MoveRecord:
	urls: tuple


class UndoHistory:
	"""A small LIFO stack; records contain immutable URL snapshots."""

	def __init__(self):
		self._records = []

	def record(self, entry):
		if entry.urls:
			self._records.append(entry)

	def pop(self):
		if self._records:
			return self._records.pop()

	def clear(self):
		self._records[:] = []


history = UndoHistory()


def record_transfer(record_type, transfers, destinations_that_existed, exists):
	urls = tuple(
		(src_url, dst_url) for src_url, dst_url in transfers
		if dst_url not in destinations_that_existed and exists(dst_url)
	)
	history.record(record_type(urls))
