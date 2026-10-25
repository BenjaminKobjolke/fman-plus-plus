from fman.impl.util.settings import Settings
from fman.impl.widgets import MainWindow
from fman.impl.window_chrome import MENU_BAR_SETTING, STATUS_BAR_SETTING, \
	TITLE_BAR_SETTING, PANE_STATUS_LINES_VISIBLE_SETTING, \
	PANE_MESSAGES_IN_STATUS_BAR_SETTING, PaneStatusSettings, WindowChrome
from fman.impl.pane_status import PaneStatusMode
from json import dump, load
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock

# One row per bar: the settings key, the WindowChrome methods that read and
# flip it, and the MainWindow setter it drives. All three bars behave
# identically except for that setter, so every test below runs over this table.
_BARS = (
	('title bar', TITLE_BAR_SETTING, 'is_title_bar_visible',
	 'toggle_title_bar', 'set_title_bar_visible'),
	('menu bar', MENU_BAR_SETTING, 'is_menu_bar_visible',
	 'toggle_menu_bar', 'set_menu_bar_visible'),
	('status bar', STATUS_BAR_SETTING, 'is_status_bar_visible',
	 'toggle_status_bar', 'set_status_bar_visible')
)

# "Caller said nothing", as distinct from an explicit help_menu=None.
_UNSET = object()

class WindowChromeTest(TestCase):

	"""
	The saved state of the window's three bars. WindowChrome is the source
	of truth, not the widget: at startup it runs before show(), when nothing
	is visible yet.
	"""

	def test_bars_are_visible_by_default(self):
		chrome = self._make_chrome()
		for name, _, is_visible, _, _ in _BARS:
			with self.subTest(name):
				self.assertTrue(getattr(chrome, is_visible)())
	def test_toggling_hides_the_bar_and_saves_it(self):
		for name, key, is_visible, toggle, setter in _BARS:
			with self.subTest(name):
				chrome = self._make_chrome()
				getattr(chrome, toggle)(self._window)
				getattr(self._window, setter).assert_called_once_with(False)
				self.assertFalse(getattr(chrome, is_visible)())
				self.assertEqual({key: False}, self._read_settings_file())
	def test_toggling_back_removes_the_key(self):
		# Absent means "visible", so the file must not end up carrying the
		# default around - see the note at TITLE_BAR_SETTING.
		for name, _, is_visible, toggle, setter in _BARS:
			with self.subTest(name):
				chrome = self._make_chrome()
				getattr(chrome, toggle)(self._window)
				getattr(chrome, toggle)(self._window)
				getattr(self._window, setter).assert_called_with(True)
				self.assertTrue(getattr(chrome, is_visible)())
				self.assertEqual({}, self._read_settings_file())
	def test_apply_pushes_the_saved_values(self):
		chrome = self._make_chrome({
			TITLE_BAR_SETTING: False, MENU_BAR_SETTING: False,
			STATUS_BAR_SETTING: False,
			PANE_STATUS_LINES_VISIBLE_SETTING: False,
			PANE_MESSAGES_IN_STATUS_BAR_SETTING: False
		})
		chrome.apply(self._window)
		for name, _, _, _, setter in _BARS:
			with self.subTest(name):
				getattr(self._window, setter).assert_called_once_with(False)
		self._window.set_pane_status_mode.assert_called_once_with(
			PaneStatusMode(lines_visible=False, in_status_bar=False))
	def test_apply_without_saved_values_shows_every_bar(self):
		self._make_chrome().apply(self._window)
		for name, _, _, _, setter in _BARS:
			with self.subTest(name):
				getattr(self._window, setter).assert_called_once_with(True)
		self._window.set_pane_status_mode.assert_called_once_with(
			PaneStatusMode(lines_visible=True, in_status_bar=True))
	def _make_chrome(self, saved=None):
		# A fresh window and a fresh settings file per call, so the calls and
		# the JSON of one subTest never reach the next one.
		self._window = MagicMock(spec=MainWindow)
		# The pane API is added in the next checkpoint, but chrome owns this
		# forwarding contract already.
		self._window.set_pane_status_mode = MagicMock()
		with open(self._settings_path, 'w') as f:
			dump(saved or {}, f)
		return WindowChrome(Settings(self._settings_path))
	def _read_settings_file(self):
		with open(self._settings_path, 'r') as f:
			return load(f)
	def setUp(self):
		self._tmp_dir = TemporaryDirectory()
		self.addCleanup(self._tmp_dir.cleanup)
		self._settings_path = join(self._tmp_dir.name, 'Settings.json')
		self._window = MagicMock(spec=MainWindow)

class MenuBarSetterTest(TestCase):

	"""
	What set_menu_bar_visible actually hides: the Help menu itself, not the
	bar around it. Off Mac there is no Help menu at all - and menuBar() would
	silently create an empty one just to hide it - while on Mac the bar is the
	system one, which ignores setVisible.

	Calls the undecorated function: run_in_main_thread needs a QApplication.
	Same approach as fman_unittest.impl.model.test_model.
	"""

	def test_without_a_help_menu_the_menu_bar_is_left_alone(self):
		window = self._make_window(help_menu=None)
		MainWindow.set_menu_bar_visible.__wrapped__(window, False)
		window.menuBar.assert_not_called()
	def test_the_help_menu_follows_the_setting(self):
		for visible in (True, False):
			with self.subTest(visible=visible):
				window = self._make_window()
				MainWindow.set_menu_bar_visible.__wrapped__(window, visible)
				window._help_menu.menuAction.return_value.setVisible \
					.assert_called_once_with(visible)
	def _make_window(self, help_menu=_UNSET):
		window = MagicMock(spec=MainWindow)
		# _help_menu is an instance attribute, so spec= does not know it.
		window._help_menu = MagicMock() if help_menu is _UNSET else help_menu
		return window

class PaneStatusSettingsTest(TestCase):

	def test_mode_defaults_both_settings_to_enabled(self):
		settings = self._make_settings()
		self.assertEqual(
			PaneStatusMode(lines_visible=True, in_status_bar=True),
			PaneStatusSettings(settings).mode())

	def test_toggling_each_setting_persists_false_and_removes_default(self):
		for key, toggle_name in (
			(PANE_STATUS_LINES_VISIBLE_SETTING, 'toggle_lines_visible'),
			(PANE_MESSAGES_IN_STATUS_BAR_SETTING, 'toggle_in_status_bar')
		):
			with self.subTest(setting=key):
				settings = self._make_settings()
				pane_status = PaneStatusSettings(settings)
				getattr(pane_status, toggle_name)(self._window)
				self.assertEqual({key: False}, self._read_settings_file())
				self.assertEqual(
					PaneStatusMode(
						lines_visible=key != PANE_STATUS_LINES_VISIBLE_SETTING,
						in_status_bar=key != PANE_MESSAGES_IN_STATUS_BAR_SETTING),
					pane_status.mode())
				getattr(pane_status, toggle_name)(self._window)
				self.assertEqual({}, self._read_settings_file())

	def test_copies_to_status_bar_for_all_setting_combinations(self):
		for lines_visible in (True, False):
			for in_status_bar in (True, False):
				with self.subTest(
					lines_visible=lines_visible,
					in_status_bar=in_status_bar):
					mode = PaneStatusMode(lines_visible, in_status_bar)
					self.assertEqual(
						in_status_bar or not lines_visible,
						mode.copies_to_status_bar)

	def _make_settings(self, saved=None):
		with open(self._settings_path, 'w') as f:
			dump(saved or {}, f)
		return Settings(self._settings_path)
	def _read_settings_file(self):
		with open(self._settings_path, 'r') as f:
			return load(f)
	def setUp(self):
		self._tmp_dir = TemporaryDirectory()
		self.addCleanup(self._tmp_dir.cleanup)
		self._settings_path = join(self._tmp_dir.name, 'Settings.json')
		self._window = MagicMock(spec=MainWindow)
		self._window.set_pane_status_mode = MagicMock()

class StatusBarSetterTest(TestCase):

	"""
	The plain one: an ordinary child widget, so the setter just hides it. No
	window flags, no native menu. Undecorated for the same reason as above.
	"""

	def test_the_status_bar_follows_the_setting(self):
		for visible in (True, False):
			with self.subTest(visible=visible):
				window = MagicMock(spec=MainWindow)
				# An instance attribute, so spec= does not know it:
				window._status_bar = MagicMock()
				MainWindow.set_status_bar_visible.__wrapped__(window, visible)
				window._status_bar.setVisible.assert_called_once_with(visible)
