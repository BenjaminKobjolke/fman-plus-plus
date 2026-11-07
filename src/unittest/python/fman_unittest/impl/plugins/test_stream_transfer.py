from io import BytesIO
from unittest import TestCase

from fman import Task
from fman import fs as fs_api
from fman.fs import FileSystem
from fman.impl.plugins.mother_fs import MotherFileSystem


class StreamTransferTest(TestCase):
	def test_copy_file_streams_bytes_when_native_copy_is_unsupported(self):
		source = MemoryFileSystem('mema', {'file.bin': b'hello\x00world'})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		run_tasks(mother_fs.prepare_copy('mema://file.bin', 'memb://copy.bin'))

		self.assertEqual(b'hello\x00world', destination.files['copy.bin'])

	def test_direct_copy_streams_after_both_native_methods_decline(self):
		source = MemoryFileSystem('mema', {'file.bin': b'data'})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		mother_fs.copy('mema://file.bin', 'memb://copy.bin')

		self.assertEqual(b'data', destination.files['copy.bin'])

	def test_copy_folder_streams_files_recursively_and_creates_folders_first(self):
		source = MemoryFileSystem('mema', {
			'folder': None,
			'folder/top.txt': b'top',
			'folder/child': None,
			'folder/child/nested.bin': b'\x00\xff'
		})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		run_tasks(mother_fs.prepare_copy('mema://folder', 'memb://folder'))

		self.assertEqual({
			'folder': None,
			'folder/top.txt': b'top',
			'folder/child': None,
			'folder/child/nested.bin': b'\x00\xff'
		}, destination.files)

	def test_move_deletes_source_files_and_empty_folders_after_copy(self):
		source = MemoryFileSystem('mema', {
			'folder': None,
			'folder/child': None,
			'folder/child/file.txt': b'data'
		})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		run_tasks(mother_fs.prepare_move('mema://folder', 'memb://folder'))

		self.assertEqual({'folder': None, 'folder/child': None,
			'folder/child/file.txt': b'data'}, destination.files)
		self.assertEqual({}, source.files)

	def test_direct_move_streams_then_deletes_the_source(self):
		source = MemoryFileSystem('mema', {'file.bin': b'data'})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		mother_fs.move('mema://file.bin', 'memb://file.bin')

		self.assertEqual({'file.bin': b'data'}, destination.files)
		self.assertEqual({}, source.files)

	def test_failed_copy_keeps_source_and_removes_partial_destination(self):
		source = MemoryFileSystem('mema', {'file.bin': b'complete data'})
		destination = MemoryFileSystem('memb', fail_after=3)
		mother_fs = create_mother_fs(source, destination)
		tasks = mother_fs.prepare_copy('mema://file.bin', 'memb://partial.bin')

		with self.assertRaises(OSError):
			run_tasks(tasks)

		self.assertEqual(b'complete data', source.files['file.bin'])
		self.assertNotIn('partial.bin', destination.files)

	def test_canceled_copy_removes_partial_destination(self):
		source = MemoryFileSystem('mema', {
			'file.bin': b'x' * 20_000
		})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)
		task = mother_fs.prepare_copy('mema://file.bin', 'memb://partial.bin')[0]
		task.set_progress = lambda progress: setattr(
			task._dialog, '_was_canceled', True
		)

		with self.assertRaises(Task.Canceled):
			task()

		self.assertNotIn('partial.bin', destination.files)

	def test_no_stream_fallback_when_either_side_lacks_open(self):
		source = NoOpenFileSystem('mema', {'file.bin': b'data'})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		with self.assertRaises(NotImplementedError):
			mother_fs.prepare_copy('mema://file.bin', 'memb://copy.bin')
		self.assertEqual({}, destination.files)
		source = MemoryFileSystem('mema', {'file.bin': b'data'})
		destination = NoOpenFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)
		with self.assertRaises(NotImplementedError):
			mother_fs.prepare_copy('mema://file.bin', 'memb://copy.bin')

	def test_native_copy_keeps_priority_over_streaming(self):
		source = NativeCopyFileSystem('mema')
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		run_tasks(mother_fs.prepare_copy('mema://file.bin', 'memb://copy.bin'))

		self.assertEqual([('mema://file.bin', 'memb://copy.bin')], source.copies)
		self.assertEqual({}, destination.files)

	def test_non_unsupported_native_copy_error_does_not_fall_back(self):
		source = FailingCopyFileSystem('mema', {'file.bin': b'data'})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		with self.assertRaisesRegex(RuntimeError, 'native copy failed'):
			mother_fs.copy('mema://file.bin', 'memb://copy.bin')
		self.assertEqual({}, destination.files)

	def test_move_does_not_fall_back_without_source_delete_support(self):
		source = NoDeleteFileSystem('mema', {'file.bin': b'data'})
		destination = MemoryFileSystem('memb')
		mother_fs = create_mother_fs(source, destination)

		with self.assertRaises(NotImplementedError):
			mother_fs.prepare_move('mema://file.bin', 'memb://file.bin')
		self.assertEqual({}, destination.files)

	def test_mother_fs_open_supports_binary_and_text_modes(self):
		fs = MemoryFileSystem('mema', {'file.txt': b'hello\r\nworld'})
		mother_fs = create_mother_fs(fs)

		with mother_fs.open('mema://file.txt', 'rb') as stream:
			self.assertEqual(b'hello\r\nworld', stream.read())
		with mother_fs.open('mema://file.txt', 'r', newline='') as stream:
			self.assertEqual('hello\r\nworld', stream.read())
		with mother_fs.open('mema://new.txt', 'w', encoding='utf-8') as stream:
			stream.write('snowman: \u2603')
		self.assertEqual('snowman: \u2603'.encode('utf-8'), fs.files['new.txt'])

	def test_mother_fs_open_rejects_invalid_modes_and_unimplemented_streams(self):
		fs = MemoryFileSystem('mema', {'file.txt': b'data'})
		unsupported_fs = NoOpenFileSystem('stub', {'file.txt': b'data'})
		mother_fs = create_mother_fs(fs, unsupported_fs)

		for mode in ('a', 'r+', 'wb+'):
			with self.subTest(mode=mode), self.assertRaises(ValueError):
				mother_fs.open('mema://file.txt', mode)
		with self.assertRaises(NotImplementedError):
			mother_fs.open('stub://file.txt', 'rb')

	def test_text_stream_context_exception_is_forwarded_to_binary_stream(self):
		fs = ContextRecordingFileSystem('mema')
		mother_fs = create_mother_fs(fs)
		error = RuntimeError('caller failed')

		with self.assertRaisesRegex(RuntimeError, 'caller failed'):
			with mother_fs.open('mema://file.txt', 'w'):
				raise error

		self.assertIs(error, fs.exit_exception)

	def test_text_stream_flush_failure_still_exits_binary_stream(self):
		from unittest.mock import patch

		fs = CloseFailingFileSystem('mema')
		mother_fs = create_mother_fs(fs)
		caller_error = RuntimeError('caller failed')

		with patch(
			'fman.impl.plugins.stream_transfer.TextIOWrapper',
			return_value=FlushFailingTextWrapper(),
		):
			with self.assertRaisesRegex(RuntimeError, 'close failed') as raised:
				with mother_fs.open('mema://file.txt', 'w'):
					raise caller_error

		self.assertIs(caller_error, fs.exit_exception)
		self.assertIsInstance(raised.exception.__cause__, OSError)
		self.assertIn('flush failed', str(raised.exception.__cause__))
		self.assertIs(caller_error, raised.exception.__cause__.__context__)

	def test_public_fs_open_delegates_to_mother_fs(self):
		mother_fs = create_mother_fs(MemoryFileSystem('mema', {'file': b'data'}))
		from unittest.mock import patch

		with patch.object(fs_api, '_get_mother_fs', return_value=mother_fs):
			with fs_api.open('mema://file', 'rb') as stream:
				self.assertEqual(b'data', stream.read())


class MemoryFileSystem(FileSystem):
	def __init__(self, scheme, files=None, fail_after=None):
		super().__init__()
		self.scheme = scheme + '://'
		self.files = dict(files or {})
		self.fail_after = fail_after

	def is_dir(self, path):
		try:
			return self.files[path] is None
		except KeyError:
			raise FileNotFoundError(path)

	def iterdir(self, path):
		if not self.is_dir(path):
			raise NotADirectoryError(path)
		prefix = path + '/' if path else ''
		for candidate in self.files:
			remainder = candidate[len(prefix):] if candidate.startswith(prefix) else ''
			if remainder and '/' not in remainder:
				yield remainder

	def mkdir(self, path):
		if path in self.files:
			raise FileExistsError(path)
		parent = path.rsplit('/', 1)[0] if '/' in path else ''
		if parent and not self.is_dir(parent):
			raise FileNotFoundError(parent)
		self.files[path] = None

	def delete(self, path):
		self.files.pop(path)
		self.notify_file_removed(path)

	def open(self, path, mode):
		if mode == 'rb':
			if path not in self.files:
				raise FileNotFoundError(path)
			if self.files[path] is None:
				raise IsADirectoryError(path)
			return BytesIO(self.files[path])
		if mode != 'wb':
			raise ValueError(mode)
		return MemoryWriteStream(self, path, self.fail_after)


class MemoryWriteStream(BytesIO):
	def __init__(self, fs, path, fail_after):
		super().__init__()
		self._fs = fs
		self._path = path
		self._fail_after = fail_after

	def write(self, data):
		if self._fail_after is not None:
			remaining = self._fail_after - self.tell()
			if remaining <= 0:
				super().write(data[:0])
				raise OSError('destination write failed')
			if len(data) > remaining:
				super().write(data[:remaining])
				raise OSError('destination write failed')
		return super().write(data)

	def close(self):
		if not self.closed:
			self._fs.files[self._path] = self.getvalue()
		super().close()


class NoOpenFileSystem(FileSystem):
	def __init__(self, scheme, files=None):
		super().__init__()
		self.scheme = scheme + '://'


class NativeCopyFileSystem(MemoryFileSystem):
	def __init__(self, scheme):
		super().__init__(scheme)
		self.copies = []

	def copy(self, src_url, dst_url):
		self.copies.append((src_url, dst_url))


class FailingCopyFileSystem(MemoryFileSystem):
	def copy(self, src_url, dst_url):
		raise RuntimeError('native copy failed')


class NoDeleteFileSystem(MemoryFileSystem):
	delete = FileSystem.delete


class ContextRecordingFileSystem(MemoryFileSystem):
	def __init__(self, scheme):
		super().__init__(scheme)
		self.exit_exception = None

	def open(self, path, mode):
		return ContextRecordingStream(self)


class CloseFailingFileSystem(ContextRecordingFileSystem):
	def open(self, path, mode):
		return CloseFailingContextStream(self)


class ContextRecordingStream(BytesIO):
	def __init__(self, fs):
		super().__init__()
		self._fs = fs

	def __exit__(self, exc_type, exc_value, traceback):
		self._fs.exit_exception = exc_value
		return super().__exit__(exc_type, exc_value, traceback)


class CloseFailingContextStream(ContextRecordingStream):
	def __exit__(self, exc_type, exc_value, traceback):
		super().__exit__(exc_type, exc_value, traceback)
		raise RuntimeError('close failed')


class FlushFailingTextWrapper:
	def flush(self):
		raise OSError('flush failed')

	def detach(self):
		pass


def create_mother_fs(*file_systems):
	mother_fs = MotherFileSystem(None)
	for fs in file_systems:
		mother_fs.add_child(fs.scheme, fs)
	return mother_fs


def run_tasks(tasks):
	for task in tasks:
		task()
