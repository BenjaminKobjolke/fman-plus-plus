"""
Indexes the files and folders below one folder for the @ file mention popup
(core/commands/file_mention.py), level by level on a background thread.

Level by level - the folder itself, then every subfolder's first level, and
so on - rather than depth-first: the popup shows hits while the walk runs,
and the near ones are what the user is most likely after. A depth-first
walk would first sink into the first subfolder's whole tree.

No fman import (like quicksearch_matchers.py), so the walk is testable
without Qt. The JustSearch plugin's scanner._scan_dir walks the same way;
neither may import the other, so a fix to one walk likely belongs in both.
"""
from collections import deque, namedtuple
from os.path import join
from threading import Event, Lock, Thread
from time import monotonic

import os

IndexEntry = namedtuple('IndexEntry', ('path', 'rel_path', 'is_dir'))

# Hard safety cap for huge trees (a drive root), not a setting: the popup
# filters the whole list per keystroke on the GUI thread.
MAX_ENTRIES = 200_000
REFRESH_INTERVAL_SECONDS = 0.15

class FileMentionIndex:
	def __init__(self, root_path, excluded):
		# `excluded`: lower-case folder names that are neither listed nor
		# entered.
		self._root = root_path
		self._excluded = excluded
		self._entries = []
		self._lock = Lock()
		self._stop = Event()
		self._done = False
		self._refresh = None
		self._last_refresh = 0
	def start(self):
		Thread(target=self._run, daemon=True).start()
	def stop(self):
		self._stop.set()
	def set_refresh(self, fn):
		self._refresh = fn
	def snapshot(self):
		with self._lock:
			return list(self._entries)
	@property
	def done(self):
		return self._done
	def _run(self):
		try:
			self._walk()
		finally:
			self._done = True
			self._notify(force=True)
	def _walk(self):
		folders = deque([(self._root, '')])
		while folders:
			folder, rel_folder = folders.popleft()
			try:
				entries = os.scandir(folder)
			except OSError:
				continue
			with entries:
				for entry in entries:
					if self._stop.is_set() or len(self._entries) >= MAX_ENTRIES:
						return
					try:
						# follow_symlinks=False guards against junction cycles
						is_dir = entry.is_dir(follow_symlinks=False)
					except OSError:
						continue
					if is_dir and entry.name.lower() in self._excluded:
						continue
					rel_path = join(rel_folder, entry.name)
					with self._lock:
						self._entries.append(IndexEntry(entry.path, rel_path, is_dir))
					if is_dir:
						folders.append((entry.path, rel_path))
			self._notify()
	def _notify(self, force=False):
		now = monotonic()
		if not force and now - self._last_refresh < REFRESH_INTERVAL_SECONDS:
			return
		self._last_refresh = now
		if self._refresh is not None:
			self._refresh()
