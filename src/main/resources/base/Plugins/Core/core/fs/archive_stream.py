"""Open individual archive entries through temporary files."""

from core.fs.zip import Extract
from fman.url import as_url
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory


def open_entry(zip_fs, path, mode):
	if mode not in ('rb', 'wb'):
		raise ValueError("Mode must be 'rb' or 'wb'.")
	zip_path, path_in_archive = zip_fs._split(path)
	if not path_in_archive:
		raise IsADirectoryError(path)
	if mode == 'rb':
		if zip_fs.is_dir(path):
			raise IsADirectoryError(path)
		tmp_dir = TemporaryDirectory()
		tmp_path = Path(tmp_dir.name, *path_in_archive.split('/'))
		tmp_path.parent.mkdir(parents=True, exist_ok=True)
		try:
			Extract(
				zip_fs._fs, zip_fs._7zip_archive(zip_path), path_in_archive,
				str(tmp_path)
			)()
			return _ArchiveEntryStream(
				open(tmp_path, 'rb'), tmp_dir, zip_fs, path, writing=False
			)
		except Exception:
			tmp_dir.cleanup()
			raise

	parent = str(PurePosixPath(path_in_archive).parent)
	if parent != '.' and not zip_fs.exists(zip_path + '/' + parent):
		raise FileNotFoundError(zip_path + '/' + parent)
	tmp_dir = TemporaryDirectory()
	tmp_path = Path(tmp_dir.name, 'archive-entry')
	try:
		return _ArchiveEntryStream(
			open(tmp_path, 'wb'), tmp_dir, zip_fs, path, writing=True
		)
	except Exception:
		tmp_dir.cleanup()
		raise


class _ArchiveEntryStream:
	def __init__(self, stream, tmp_dir, zip_fs, path, writing):
		self._stream = stream
		self._tmp_dir = tmp_dir
		self._zip_fs = zip_fs
		self._path = path
		self._writing = writing
		self._closed = False

	@property
	def name(self):
		return self._stream.name

	def __getattr__(self, name):
		return getattr(self._stream, name)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close(commit=exc_type is None)
		return False

	def close(self, commit=True):
		if self._closed:
			return
		try:
			self._stream.close()
			if self._writing and commit:
				self._zip_fs.copy(
					as_url(self.name), as_url(self._path, self._zip_fs.scheme)
				)
		finally:
			self._closed = True
			self._tmp_dir.cleanup()
