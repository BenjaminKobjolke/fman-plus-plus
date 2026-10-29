from core.libmpv import (
	LIBMPV_DLL_NAME, _DownloadLibmpv, cache_dir, ensure_libmpv_on_path,
)
import core.libmpv
from fman import DATA_DIRECTORY
from os.path import join
from unittest import TestCase
from unittest.mock import MagicMock, patch

import os
import requests
import tempfile

class ExtractTest(TestCase):
	def test_uses_shared_seven_zip_binary(self):
		with tempfile.TemporaryDirectory() as tmp:
			with patch('core.libmpv.cache_dir', return_value=tmp), \
					patch('core.libmpv.run') as run, \
					patch('core.fs.zip.SEVEN_ZIP_BINARY', 'shared-7zip'):
				run.return_value.returncode = 0
				core.libmpv._extract(b'archive')
		self.assertEqual('shared-7zip', run.call_args.args[0][0])

class CacheDirTest(TestCase):
	def test_returns_data_directory_local_libmpv(self):
		self.assertEqual(join(DATA_DIRECTORY, 'Local', 'libmpv'), cache_dir())

class EnsureLibmpvOnPathTest(TestCase):
	def setUp(self):
		self._original_path = os.environ['PATH']

	def tearDown(self):
		os.environ['PATH'] = self._original_path

	def test_non_windows_is_a_noop(self):
		original_environment = dict(os.environ)
		with patch('core.libmpv.sys.platform', 'linux'), \
				patch('core.libmpv.submit_task') as submit:
			ensure_libmpv_on_path()
		submit.assert_not_called()
		self.assertEqual(self._original_path, os.environ['PATH'])
		self.assertEqual(original_environment, dict(os.environ))

	def test_darwin_adds_homebrew_to_dyld_fallback_path(self):
		with patch('core.libmpv.sys.platform', 'darwin'), \
				patch.dict(os.environ, {}, clear=True):
			ensure_libmpv_on_path()
			self.assertEqual(
				'~/lib:/usr/local/lib:/lib:/usr/lib:/opt/homebrew/lib',
				os.environ['DYLD_FALLBACK_LIBRARY_PATH'],
			)

	def test_darwin_adds_homebrew_path_only_once(self):
		with patch('core.libmpv.sys.platform', 'darwin'), \
				patch.dict(os.environ, {
					'DYLD_FALLBACK_LIBRARY_PATH': '/custom/lib:/opt/homebrew/lib',
				}, clear=True):
			ensure_libmpv_on_path()
			self.assertEqual(
				'/custom/lib:/opt/homebrew/lib',
				os.environ['DYLD_FALLBACK_LIBRARY_PATH'],
			)

	def test_cache_hit_skips_download_and_prepends_path_once(self):
		with tempfile.TemporaryDirectory() as tmp:
			open(join(tmp, LIBMPV_DLL_NAME), 'w').close()
			with patch('core.libmpv.sys.platform', 'win32'), \
					patch('core.libmpv.cache_dir', return_value=tmp), \
					patch('core.libmpv.submit_task') as submit:
				ensure_libmpv_on_path()
				ensure_libmpv_on_path()
			submit.assert_not_called()
			path_entries = os.environ['PATH'].split(os.pathsep)
			self.assertEqual(1, path_entries.count(tmp))

	def test_cache_miss_downloads_then_prepends_path(self):
		with tempfile.TemporaryDirectory() as tmp:
			def fake_submit(_task):
				open(join(tmp, LIBMPV_DLL_NAME), 'w').close()
			with patch('core.libmpv.sys.platform', 'win32'), \
					patch('core.libmpv.cache_dir', return_value=tmp), \
					patch(
						'core.libmpv.submit_task', side_effect=fake_submit,
					) as submit:
				ensure_libmpv_on_path()
			submit.assert_called_once()
			self.assertIn(tmp, os.environ['PATH'].split(os.pathsep))

	def test_failed_or_canceled_download_raises_and_does_not_touch_path(self):
		# fman.submit_task() swallows Task.Canceled internally and otherwise
		# returns once the task callable finishes/raises - either way, if
		# the dll still isn't on disk afterwards (download failed, or the
		# user hit Cancel in the progress dialog), ensure_libmpv_on_path
		# must not let the caller proceed as if libmpv were available.
		with tempfile.TemporaryDirectory() as tmp:
			with patch('core.libmpv.sys.platform', 'win32'), \
					patch('core.libmpv.cache_dir', return_value=tmp), \
					patch('core.libmpv.submit_task'):
				self.assertRaises(RuntimeError, ensure_libmpv_on_path)
			self.assertEqual(self._original_path, os.environ['PATH'])

class DownloadLibmpvTest(TestCase):
	def test_hash_mismatch_raises_before_extracting(self):
		response = MagicMock(spec=requests.Response)
		response.headers = {'Content-Length': '21'}
		response.iter_content.return_value = [b'not the real archive']
		with patch('core.libmpv.requests.get', return_value=response), \
				patch('core.libmpv._extract') as extract:
			self.assertRaises(ValueError, _DownloadLibmpv())
		extract.assert_not_called()
