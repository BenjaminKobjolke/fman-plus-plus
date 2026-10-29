"""
Ensures the native libmpv-2.dll (required by python-mpv, see core/videoviewer.py)
is available on Windows, downloading and caching it on first use.

Not bundled in the repo: LGPL builds like this one may be redistributed, but
fetching from upstream on first use avoids shipping a ~30 MB binary in git and
keeps fman itself from redistributing it at all - same pattern apps use for
ffmpeg. macOS/Linux are expected to install mpv via the system package manager
(brew/apt). On Apple Silicon, Homebrew installs libmpv under /opt/homebrew/lib,
which dyld does not search by default, so that directory is added to its fallback path.

Pinned to a specific LGPLv2.1+ build from zhongfly/mpv-winbuild (not the more
common shinchiro/mpv-winbuild-cmake builds, which are GPL-2.0-or-later by
default) - verified by SHA-256 before use.

A %PATH% prepend (not os.add_dll_directory()) is what's needed: python-mpv
resolves the DLL itself via ctypes.util.find_library(), which on Windows
scans %PATH% for the file and hands CDLL the resulting absolute path -
add_dll_directory() is never consulted by that lookup. Confirmed end-to-end
during development: prepending %PATH% and then `import mpv` succeeds.

The download runs via fman's own Task/submit_task machinery (the same one
core/commands/ uses for copy/move/delete/rename), which gives a
real byte-accurate QProgressDialog for free and - just as importantly - is
designed to be driven from a background thread. ensure_libmpv_on_path() must
be called from show_video_viewer() *before* it hands off to the
@run_in_main_thread-wrapped Qt widget code, not from within it: fman already
runs each DirectoryPaneCommand's __call__ on its own background thread (see
PaneCommandRegistry._run_outside_main_thread), so calling this from there
keeps the Qt event loop free during the download instead of freezing the
whole app for its multi-second duration.
"""
from fman import DATA_DIRECTORY, Task, submit_task
from os.path import join
from subprocess import run

import hashlib
import os
import requests
import sys
import tempfile

LIBMPV_VERSION = '2026-08-22-b955aa28f3'
LIBMPV_URL = (
	'https://github.com/zhongfly/mpv-winbuild/releases/download/'
	'2026-08-22-b955aa28f3/mpv-dev-lgpl-x86_64-20260822-git-b955aa28f3.7z'
)
LIBMPV_SHA256 = \
	'a932332b15293f3fbf673ff78b08824de73af7da637fabb472163092a2d7861f'
LIBMPV_DLL_NAME = 'libmpv-2.dll'
HOMEBREW_LIBRARY_DIR = '/opt/homebrew/lib'
DYLD_DEFAULT_FALLBACK_LIBRARY_PATH = '~/lib:/usr/local/lib:/lib:/usr/lib'
DYLD_LIBRARY_PATH_SEPARATOR = ':'

def cache_dir():
	return join(DATA_DIRECTORY, 'Local', 'libmpv')

def ensure_libmpv_on_path():
	"""
	Blocks (on the calling background thread - see module docstring) until
	libmpv-2.dll is cached, downloading it with a real progress dialog if
	needed. Raises if the download/verification/extraction fails, or if the
	user cancels the dialog - callers must not proceed to import mpv or open
	the video view in that case.
	"""
	if sys.platform == 'darwin':
		fallback_path = os.environ.get(
			'DYLD_FALLBACK_LIBRARY_PATH', DYLD_DEFAULT_FALLBACK_LIBRARY_PATH
		).split(DYLD_LIBRARY_PATH_SEPARATOR)
		if HOMEBREW_LIBRARY_DIR not in fallback_path:
			fallback_path.append(HOMEBREW_LIBRARY_DIR)
			os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = (
				DYLD_LIBRARY_PATH_SEPARATOR.join(fallback_path)
			)
		return
	if sys.platform != 'win32':
		return
	dll_path = join(cache_dir(), LIBMPV_DLL_NAME)
	if not os.path.isfile(dll_path):
		submit_task(_DownloadLibmpv())
		if not os.path.isfile(dll_path):
			raise RuntimeError('libmpv download did not complete')
	_prepend_to_path(cache_dir())

def _prepend_to_path(directory):
	if directory not in os.environ['PATH'].split(os.pathsep):
		os.environ['PATH'] = directory + os.pathsep + os.environ['PATH']

class _DownloadLibmpv(Task):

	_CHUNK_SIZE = 1 << 18

	def __init__(self):
		super().__init__('Downloading video player component (one-time)...')

	def __call__(self):
		response = requests.get(LIBMPV_URL, stream=True, timeout=30)
		response.raise_for_status()
		self.set_size(int(response.headers.get('Content-Length', 0)))
		digest = hashlib.sha256()
		downloaded = 0
		chunks = []
		for chunk in response.iter_content(chunk_size=self._CHUNK_SIZE):
			self.check_canceled()
			if not chunk:
				continue
			digest.update(chunk)
			chunks.append(chunk)
			downloaded += len(chunk)
			self.set_progress(downloaded)
		if digest.hexdigest() != LIBMPV_SHA256:
			raise ValueError(
				'libmpv download hash mismatch (expected %s, got %s)'
				% (LIBMPV_SHA256, digest.hexdigest())
			)
		self.set_text('Extracting...')
		_extract(b''.join(chunks))

def _extract(archive):
	# Import lazily to avoid loading the archive filesystem until extraction.
	from core.fs.zip import SEVEN_ZIP_BINARY
	os.makedirs(cache_dir(), exist_ok=True)
	with tempfile.NamedTemporaryFile(suffix='.7z', delete=False) as f:
		f.write(archive)
		archive_path = f.name
	try:
		result = run(
			[
				SEVEN_ZIP_BINARY, 'e', archive_path, LIBMPV_DLL_NAME,
				'-o' + cache_dir(), '-y',
			],
			capture_output=True, text=True,
		)
		if result.returncode != 0:
			raise RuntimeError(
				'7-Zip extraction of %s failed: %s'
				% (LIBMPV_DLL_NAME, result.stderr)
			)
	finally:
		os.remove(archive_path)
