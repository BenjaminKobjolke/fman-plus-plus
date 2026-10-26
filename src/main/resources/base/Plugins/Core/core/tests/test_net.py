import os
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import URLError

from core import net
from fman import Task


class _Response:
	def __init__(self, chunks):
		self.chunks = iter(chunks)
		self.headers = {'Content-Length': '9'}

	def __enter__(self):
		return self

	def __exit__(self, *_args):
		pass

	def read(self, _size):
		return next(self.chunks, b'')


class _FailingResponse(_Response):
	def read(self, _size):
		raise URLError('connection dropped')


class _RequestsResponse(_Response):
	status_code = 200
	reason = 'OK'

	def iter_content(self, chunk_size):
		return self.chunks


class DownloadTest(TestCase):
	def test_urlopen_read_error_falls_back_to_requests(self):
		task = Mock(spec=Task)
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, 'update.exe')
			with patch.object(net, 'urlopen', return_value=_FailingResponse([])):
				with patch.object(
					net.requests, 'get',
					return_value=_RequestsResponse([b'payload'])
				) as get:
					net.download('https://example.test/update.exe', path, task)

			with open(path, 'rb') as downloaded:
				self.assertEqual(b'payload', downloaded.read())
			get.assert_called_once_with(
				'https://example.test/update.exe', stream=True
			)

	def test_download_writes_content_and_reports_progress(self):
		task = Mock(spec=Task)
		with patch.object(
			net, 'urlopen', return_value=_Response([b'abc', b'def', b'ghi'])
		):
			with tempfile.TemporaryDirectory() as directory:
				path = os.path.join(directory, 'update.exe')
				net.download('https://example.test/update.exe', path, task)

				with open(path, 'rb') as downloaded:
					self.assertEqual(b'abcdefghi', downloaded.read())
				task.set_size.assert_called_once_with(9)
				self.assertEqual(
					[3, 6, 9],
					[call.args[0] for call in task.set_progress.call_args_list]
				)
				self.assertEqual(3, task.check_canceled.call_count)

	def test_cancelled_download_removes_partial_and_final_files(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, 'update.exe')
			task = Mock(spec=Task)
			task.check_canceled.side_effect = [None, Task.Canceled()]
			with patch.object(
				net, 'urlopen', return_value=_Response([b'abc', b'def', b'ghi'])
			):
				with self.assertRaises(Task.Canceled):
					net.download('https://example.test/update.exe', path, task)

			self.assertFalse(os.path.exists(path + '.part'))
			self.assertFalse(os.path.exists(path))
