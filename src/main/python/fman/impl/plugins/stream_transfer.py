"""Copy and move files between file systems through binary streams."""

from io import TextIOWrapper
from typing import Sequence

from fman import Task
from fman.fs import FileSystem
from fman.url import basename


CHUNK_SIZE = 16 * 1024


def binary_mode(mode):
	if mode in ('rb', 'wb'):
		return mode
	if mode == 'r':
		return 'rb'
	if mode == 'w':
		return 'wb'
	raise ValueError('Mode must be one of r, rb, w, or wb.')


def is_text_mode(mode):
	return mode in ('r', 'w')


class TextStream:
	"""Add text encoding while preserving the binary stream's context exit."""

	def __init__(self, binary_stream, encoding=None, errors=None, newline=None):
		self._binary_stream = binary_stream
		self._text_stream = TextIOWrapper(
			binary_stream, encoding=encoding, errors=errors, newline=newline
		)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		failures = []
		for cleanup in (
			self._text_stream.flush,
			self._text_stream.detach,
			lambda: self._binary_stream.__exit__(exc_type, exc_value, traceback),
		):
			try:
				result = cleanup()
			except BaseException as error:
				failures.append(error)
		for previous, current in zip(failures, failures[1:]):
			current.__context__ = previous
		if failures:
			if len(failures) > 1:
				raise failures[-1] from failures[-2]
			raise failures[0]
		return result

	def __getattr__(self, name):
		return getattr(self._text_stream, name)


def supports_open(fs):
	method = getattr(fs, 'open', None)
	return getattr(method, '__func__', method) is not FileSystem.open


def can_stream(src_fs, dst_fs, for_move=False):
	if not supports_open(src_fs) or not supports_open(dst_fs):
		return False
	return not for_move or _overrides(src_fs, 'delete')


def prepare_stream_copy(mother_fs, src_url, dst_url):
	tasks = []
	_append_copy_tasks(mother_fs, src_url, dst_url, tasks)
	return tasks


def prepare_stream_move(mother_fs, src_url, dst_url):
	tasks = []
	_append_move_tasks(mother_fs, src_url, dst_url, tasks)
	return tasks


def _append_copy_tasks(mother_fs, src_url, dst_url, tasks):
	if not mother_fs.is_dir(src_url):
		tasks.append(StreamCopyFile(mother_fs, src_url, dst_url))
		return

	directory_task = Task(
		'Creating ' + basename(dst_url), fn=mother_fs.makedirs,
		args=(dst_url,), kwargs={'exist_ok': True}
	)
	directory_task.blocks_later_tasks = True
	tasks.append(directory_task)
	for name in mother_fs.iterdir(src_url):
		_append_copy_tasks(
			mother_fs, _join_url(src_url, name), _join_url(dst_url, name), tasks
		)


def _append_move_tasks(mother_fs, src_url, dst_url, tasks):
	if not mother_fs.is_dir(src_url):
		copy_task = StreamCopyFile(mother_fs, src_url, dst_url)
		tasks.append(MoveByCopy(mother_fs, src_url, dst_url, [copy_task]))
		return

	directory_task = Task(
		'Creating ' + basename(dst_url), fn=mother_fs.makedirs,
		args=(dst_url,), kwargs={'exist_ok': True}
	)
	directory_task.blocks_later_tasks = True
	tasks.append(directory_task)
	for name in mother_fs.iterdir(src_url):
		_append_move_tasks(
			mother_fs, _join_url(src_url, name), _join_url(dst_url, name), tasks
		)
	tasks.append(DeleteDirIfEmpty(mother_fs, src_url))


def _join_url(url, name):
	return url.rstrip('/') + '/' + name


def _overrides(fs, method_name):
	method = getattr(fs, method_name)
	base_method = getattr(FileSystem, method_name)
	return getattr(method, '__func__', method) is not base_method


class StreamCopyFile(Task):
	"""Copy one file in bounded chunks, removing an incomplete destination."""

	def __init__(self, mother_fs, src_url, dst_url):
		size = _get_size(mother_fs, src_url)
		super().__init__('Copying ' + basename(src_url), size=size)
		self._mother_fs = mother_fs
		self._src_url = src_url
		self._dst_url = dst_url

	def __call__(self):
		written = 0
		destination_opened = False
		try:
			with self._mother_fs.open(self._src_url, 'rb') as source:
				with self._mother_fs.open(self._dst_url, 'wb') as destination:
					destination_opened = True
					while True:
						self.check_canceled()
						chunk = source.read(CHUNK_SIZE)
						if not chunk:
							break
						destination.write(chunk)
						written += len(chunk)
						self.set_progress(written)
			self._mother_fs.notify_file_added(self._dst_url)
		except BaseException:
			if destination_opened:
				try:
					self._mother_fs.delete(self._dst_url)
				except Exception:
					pass
			raise


def _get_size(mother_fs, url):
	try:
		size = mother_fs.query(url, 'size_bytes')
	except Exception:
		return 0
	return size if isinstance(size, int) and size >= 0 else 0


class DeleteDirIfEmpty(Task):
	"""Remove a moved source directory after its contents were copied."""

	waits_for_earlier_tasks = True

	def __init__(self, mother_fs, url):
		super().__init__('Removing ' + basename(url), size=1)
		self._mother_fs = mother_fs
		self._url = url

	def __call__(self):
		try:
			next(iter(self._mother_fs.iterdir(self._url)))
		except StopIteration:
			try:
				self._mother_fs.delete(self._url)
			except OSError:
				pass


class MoveByCopy(Task):
	"""Copy an item to its destination before deleting its source."""

	def __init__(
		self, fs: FileSystem, src_url: str, dst_url: str,
		copy_tasks: Sequence[Task]
	) -> None:
		size = sum(task.get_size() for task in copy_tasks)
		super().__init__('Moving ' + basename(src_url), size=size)
		self._fs = fs
		self._src_url = src_url
		self._dst_url = dst_url
		self._copy_tasks = copy_tasks

	def __call__(self) -> None:
		for task in self._copy_tasks:
			self.run(task)
		self.check_canceled()
		if not self._fs.exists(self._dst_url):
			raise OSError(
				'Copy completed but the destination is missing; the source was kept.'
			)
		self._fs.delete(self._src_url)
