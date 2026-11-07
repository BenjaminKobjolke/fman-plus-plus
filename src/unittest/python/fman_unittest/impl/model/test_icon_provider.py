from fman import PLATFORM
from fman.impl.model.icon_provider import IconProvider, overlay_icons_enabled
from fman.impl.model.table import Row
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipIf
from unittest.mock import patch

_TXT = 'file://C:/dir/notes.txt'
_DIR = 'file://C:/dir/sub'
_UNKNOWN = 'file://C:/dir/x.none'
_ICO = 'file://C:/dir/favicon.ico'
_EXE = 'file://C:/dir/adb.exe'
_LNK = 'file://C:/dir/adb.lnk'
_OTHER_TXT = 'file://C:/other/other.txt'
_MODIFIED_TXT = 'file://C:/other/modified.txt'
_NETWORK_TXT = 'file:////server/share/notes.txt'

# "no icon set argument was passed", which is not the same as passing None.
_UNSET = object()

class OverlayIconSettingTest(TestCase):

	def test_overlay_setting_is_enabled_on_windows(self):
		with patch('fman.impl.model.icon_provider.PLATFORM', 'Windows'), patch(
			'fman.impl.model.icon_provider.load_json',
			return_value={'shell_overlay_icons': True}
		):
			self.assertTrue(overlay_icons_enabled())

	def test_overlay_setting_is_ignored_off_windows(self):
		with patch('fman.impl.model.icon_provider.PLATFORM', 'Linux'), patch(
			'fman.impl.model.icon_provider.load_json',
			return_value={'shell_overlay_icons': True}
		):
			self.assertFalse(overlay_icons_enabled())

	def test_icon_provider_passes_overlay_setting_to_shell_provider(self):
		class OverlayAwareProvider(_StubQtIconProvider):
			def set_overlay_icons_enabled(self, enabled):
				self.overlay_icons_enabled = enabled

		qt_provider = OverlayAwareProvider()
		with TemporaryDirectory() as directory, patch(
			'fman.impl.model.icon_provider.PLATFORM', 'Windows'
		), patch(
			'fman.impl.model.icon_provider.load_json',
			return_value={'shell_overlay_icons': True}
		):
			provider = IconProvider(
				qt_provider, _StubFileSystem(), directory
			)
			provider.get_icon(_TXT)

		self.assertTrue(qt_provider.overlay_icons_enabled)

@skipIf(PLATFORM != 'Windows', 'Skip Windows-only test')
class NetworkIconTest(TestCase):

	"""
	Asking the Windows shell for a file's icon on a network share reads that
	file over the wire. Default to the cheap per-extension icon there; the Core
	plugin's ToggleNetworkIcons command opts back in.
	"""

	_LOCAL = 'file://C:/dir/adb.exe'
	_NETWORK = 'file:////tsclient/C/dir/adb.exe'

	def test_local_file_uses_shell_icon(self):
		self.assertEqual('C:/dir/adb.exe', self._get_icon(self._LOCAL))
	def test_network_file_uses_generic_icon(self):
		self.assertEqual(self._surrogate('.exe'), self._get_icon(self._NETWORK))
	def test_network_file_reuses_one_icon_per_suffix(self):
		self._get_icon(self._NETWORK)
		other = 'file:////tsclient/C/other/fastboot.exe'
		self.assertEqual(self._surrogate('.exe'), self._get_icon(other))
	def test_network_file_uses_shell_icon_when_enabled(self):
		icon = self._get_icon(self._NETWORK, network_file_icons=True)
		self.assertEqual('//tsclient/C/dir/adb.exe', icon)
	def _get_icon(self, url, **settings):
		with patch(
			'fman.impl.model.icon_provider.load_json', return_value=settings
		):
			return self._provider.get_icon(url)
	def _surrogate(self, suffix):
		return Path(self._cache_dir.name, 'file' + suffix).as_posix()
	def setUp(self):
		super().setUp()
		self._cache_dir = TemporaryDirectory()
		self.addCleanup(self._cache_dir.cleanup)
		self._provider = IconProvider(
			_StubQtIconProvider(), _StubFileSystem(), self._cache_dir.name
		)

class IconSetTest(TestCase):

	"""
	Which files the active icon set answers for, and which keep the icon the
	OS gives them.
	"""

	def test_no_set_uses_the_shell(self):
		self.assertEqual('C:/dir/notes.txt', self._get_icon(_TXT, None))
	def test_set_answers(self):
		self.assertEqual('svg:text', self._get_icon(_TXT))
	def test_directory(self):
		self.assertEqual('svg:folder', self._get_icon(_DIR, is_dir=True))
	def test_file_the_set_has_no_icon_for(self):
		# The set said a name, but ships no such file. Fall back to the OS
		# rather than drawing nothing.
		self.assertEqual('C:/dir/x.none', self._get_icon(_UNKNOWN))
	def test_ico_always_uses_the_shell(self):
		# An .ico *is* a picture of itself; no set can say more about it.
		self.assertEqual('C:/dir/favicon.ico', self._get_icon(_ICO))
	def test_exe_uses_the_set_by_default(self):
		self.assertEqual('svg:exe', self._get_icon(_EXE))
	def test_exe_uses_the_shell_when_opted_out(self):
		icon = self._get_icon(_EXE, os_icons_for_executables=True)
		self.assertEqual('C:/dir/adb.exe', icon)
	def test_lnk_uses_the_shell_when_opted_out(self):
		icon = self._get_icon(_LNK, os_icons_for_executables=True)
		self.assertEqual('C:/dir/adb.lnk', icon)
	def test_switching_set_drops_the_cache(self):
		self.assertEqual('svg:text', self._get_icon(_TXT))
		self._provider.set_icon_set(_StubIconSet('other'))
		self.assertEqual('other:text', self._get_icon(_TXT))
	def test_a_file_that_cannot_be_stat_ed_falls_back(self):
		# Before icon sets, drawing a file:// icon never asked the FS
		# anything. Model#_load_file tolerates an OSError from is_dir, but it
		# does not guard the icon call - so raising here would take the whole
		# directory listing down.
		self._provider._fs.is_dir_error = PermissionError('denied')
		self.assertEqual('C:/dir/notes.txt', self._get_icon(_TXT))
	def test_a_file_that_disappeared_falls_back(self):
		self._provider._fs.is_dir_error = FileNotFoundError(_TXT)
		self.assertEqual('C:/dir/notes.txt', self._get_icon(_TXT))
	def test_icons_are_reused_per_file(self):
		first = self._get_icon(_TXT)
		self.assertIs(first, self._get_icon('file://C:/elsewhere/other.txt'))
	def test_no_color_leaves_the_icon_alone(self):
		self.assertEqual('svg:text', self._get_icon(_TXT))
	def test_color_reaches_the_loader(self):
		self._provider.set_icon_color('#00ff41')
		self.assertEqual('svg:text@#00ff41', self._get_icon(_TXT))
	def test_switching_color_drops_the_cache(self):
		# The cache is keyed by file path, so without this the first color
		# would keep being drawn under the second.
		self._provider.set_icon_color('#00ff41')
		self.assertEqual('svg:text@#00ff41', self._get_icon(_TXT))
		self._provider.set_icon_color('#ff5252')
		self.assertEqual('svg:text@#ff5252', self._get_icon(_TXT))
	def test_clearing_color_drops_the_cache(self):
		self._provider.set_icon_color('#00ff41')
		self._get_icon(_TXT)
		self._provider.set_icon_color(None)
		self.assertEqual('svg:text', self._get_icon(_TXT))
	def test_switching_set_marks_existing_rows_stale(self):
		before = _row()
		self._provider.set_icon_set(_StubIconSet('other'))
		self.assertNotEqual(before, _row())
	def test_switching_color_marks_existing_rows_stale(self):
		before = _row()
		self._provider.set_icon_color('#00ff41')
		self.assertNotEqual(before, _row())
	def _get_icon(self, url, icon_set=_UNSET, **settings):
		if icon_set is not _UNSET:
			self._provider.set_icon_set(icon_set)
		with patch(
			'fman.impl.model.icon_provider.load_json', return_value=settings
		):
			return self._provider.get_icon(url)
	def setUp(self):
		super().setUp()
		self._cache_dir = TemporaryDirectory()
		self.addCleanup(self._cache_dir.cleanup)
		# The real one builds a QIcon, which needs a QApplication. The tint
		# shows up in the returned string so a test can tell the color apart:
		patcher = patch(
			'fman.impl.model.icon_provider._load_icon',
			side_effect=lambda p, color=None:
				p if color is None else '%s@%s' % (p, color)
		)
		patcher.start()
		self.addCleanup(patcher.stop)
		self._provider = IconProvider(
			_StubQtIconProvider(), _StubFileSystem(), self._cache_dir.name,
			_StubIconSet('svg')
		)

class IconSetOverlayTest(TestCase):

	def test_enabled_overlay_is_composed_over_set_icon(self):
		with patch(
			'fman.impl.model.icon_provider.overlay_icons_enabled',
			return_value=True
		), patch(
			'fman.impl.model.icon_provider.compose_overlay',
			side_effect=lambda icon, overlay: (icon, overlay)
		):
			icon = self._provider.get_icon(_TXT)

		self.assertEqual(('svg:text', 'overlay:2'), icon)
		self.assertEqual(['C:/dir/notes.txt'], self._overlay_source.paths)

	def test_composed_icon_is_cached_by_set_icon_and_overlay_index(self):
		with patch(
			'fman.impl.model.icon_provider.overlay_icons_enabled',
			return_value=True
		), patch(
			'fman.impl.model.icon_provider.compose_overlay',
			side_effect=lambda icon, overlay: (icon, overlay)
		) as compose:
			first = self._provider.get_icon(_TXT)
			second = self._provider.get_icon(_OTHER_TXT)

		self.assertIs(first, second)
		compose.assert_called_once_with('svg:text', 'overlay:2')

	def test_different_overlay_indexes_get_different_composed_icons(self):
		with patch(
			'fman.impl.model.icon_provider.overlay_icons_enabled',
			return_value=True
		), patch(
			'fman.impl.model.icon_provider.compose_overlay',
			side_effect=lambda icon, overlay: (icon, overlay)
		):
			first = self._provider.get_icon(_TXT)
			second = self._provider.get_icon(_MODIFIED_TXT)

		self.assertEqual(('svg:text', 'overlay:2'), first)
		self.assertEqual(('svg:text', 'overlay:3'), second)

	def test_disabled_overlays_do_not_query_the_shell(self):
		with patch(
			'fman.impl.model.icon_provider.overlay_icons_enabled',
			return_value=False
		):
			self.assertEqual('svg:text', self._provider.get_icon(_TXT))

		self.assertEqual([], self._overlay_source.paths)

	def test_network_overlay_is_skipped_when_network_icons_are_disabled(self):
		with patch(
			'fman.impl.model.icon_provider.overlay_icons_enabled',
			return_value=True
		), patch(
			'fman.impl.model.icon_provider._core_setting',
			return_value=False
		):
			self._provider.get_icon(_NETWORK_TXT)

		self.assertEqual([], self._overlay_source.paths)

	def test_network_overlay_is_used_when_both_settings_are_enabled(self):
		with patch(
			'fman.impl.model.icon_provider.overlay_icons_enabled',
			return_value=True
		), patch(
			'fman.impl.model.icon_provider._core_setting',
			return_value=True
		), patch(
			'fman.impl.model.icon_provider.compose_overlay',
			side_effect=lambda icon, overlay: (icon, overlay)
		):
			icon = self._provider.get_icon(_NETWORK_TXT)

		self.assertEqual(('svg:text', 'overlay:2'), icon)
		self.assertEqual(['//server/share/notes.txt'], self._overlay_source.paths)

	def test_non_file_url_does_not_query_the_windows_shell(self):
		with patch(
			'fman.impl.model.icon_provider.overlay_icons_enabled',
			return_value=True
		):
			self._provider.get_icon('sftp://host/dir/notes.txt')

		self.assertEqual([], self._overlay_source.paths)

	def setUp(self):
		super().setUp()
		self._cache_dir = TemporaryDirectory()
		self.addCleanup(self._cache_dir.cleanup)
		self._overlay_source = _StubOverlaySource()
		self._provider = IconProvider(
			_StubQtIconProvider(), _StubFileSystem(), self._cache_dir.name,
			_StubIconSet('svg'), overlay_source=self._overlay_source
		)
		patcher = patch(
			'fman.impl.model.icon_provider._load_icon',
			side_effect=lambda p, color=None:
				p if color is None else '%s@%s' % (p, color)
		)
		patcher.start()
		self.addCleanup(patcher.stop)

def _row():
	"""
	A pane row, the way Model builds one. Only its icon generation matters
	here: the panes hold rows built under the old set or color, and Row#__eq__
	ignores .icon by value - so unless the provider invalidates them, the diff
	that follows a reload reports no change. See RowEqualityTest in
	test_table.py.
	"""
	return Row('file://C:/dir/notes.txt', None, False, ('notes.txt',))

class _StubQtIconProvider:
	def icon(self, file_info):
		# The path is all we assert on - the real one returns a QIcon:
		return file_info.filePath()

class _StubFileSystem:
	def __init__(self):
		self.is_dir_error = None
	def is_dir(self, url):
		if self.is_dir_error is not None:
			raise self.is_dir_error
		return url == _DIR
	def resolve(self, url):
		return url

class _StubIconSet:

	"""
	Returns a path built from the file's extension, so a test can tell which
	set answered. "x.none" stands for a name the set maps but does not ship.
	"""

	def __init__(self, prefix):
		self._prefix = prefix
	def icon_file(self, file_name, is_dir):
		if is_dir:
			return self._prefix + ':folder'
		suffix = file_name.rsplit('.', 1)[-1]
		if suffix == 'none':
			return None
		return self._prefix + ':' + {'txt': 'text'}.get(suffix, suffix)

class _StubOverlaySource:
	def __init__(self):
		self.paths = []
	def overlay_index(self, path):
		self.paths.append(path)
		return 3 if path.endswith('modified.txt') else 2
	def pixmap(self, overlay_index):
		return 'overlay:%s' % overlay_index
