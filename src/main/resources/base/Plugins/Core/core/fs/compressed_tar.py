"""Read-only browsing of compressed TARs by decompressing their outer layer once."""

from collections import namedtuple
from core.fs.read_only_archive import _ReadOnly7ZipFileSystem
from core.fs.zip import _run_7zip
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

import os


_Entry = namedtuple('_Entry', ('stat_key', 'tmp_dir', 'tar_path'))


class _DecompressedTars:
	def __init__(self):
		self._lock = Lock()
		self._entries = {}

	def get(self, archive):
		stat = os.stat(archive)
		stat_key = (stat.st_size, stat.st_mtime_ns)
		with self._lock:
			entry = self._entries.get(archive)
			if entry is not None and entry.stat_key == stat_key:
				return entry.tar_path
			if entry is not None:
				del self._entries[archive]
				entry.tmp_dir.cleanup()
			tmp_dir = TemporaryDirectory(prefix='fman-ctar-')
			try:
				_run_7zip(['e', archive, '-o' + tmp_dir.name, '-y'])
				outputs = list(Path(tmp_dir.name).iterdir())
				if len(outputs) != 1 or not outputs[0].is_file():
					raise ValueError(
						'Expected compressed TAR to contain one decompressed file'
					)
				result = _Entry(stat_key, tmp_dir, str(outputs[0]))
				self._entries[archive] = result
				return result.tar_path
			except Exception:
				tmp_dir.cleanup()
				raise


_DECOMPRESSED = _DecompressedTars()


class CompressedTarFileSystem(_ReadOnly7ZipFileSystem):
	scheme = 'ctar://'
	read_only_message = 'Compressed TAR archives are read-only.'

	def _7zip_archive(self, zip_path):
		# shortcut: one lock for all archives, so a big unpack delays listing
		# other compressed TARs; use per-archive locks if that is noticed.
		return _DECOMPRESSED.get(zip_path)


__all__ = ['CompressedTarFileSystem']
