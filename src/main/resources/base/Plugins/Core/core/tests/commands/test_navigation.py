from core.commands import navigation
from core.commands.navigation import History
from core.tests.commands import FakePane
from fman import PLATFORM
from fman.url import as_url
from unittest import TestCase, skipUnless
from unittest.mock import patch

class _ArgRecordingPane(FakePane):
	# FakePane keeps command names only; following a shortcut is all about
	# *where* open_directory is sent.
	def run_command(self, name, args=None):
		super().run_command(name, args)
		self.args_run = args

class _PaneWindow:
	def __init__(self, panes):
		self._panes = panes
	def get_panes(self):
		return self._panes

class _NavigationPane(FakePane):
	def __init__(self, panes, url='file:///current'):
		super().__init__(_PaneWindow(panes), url)
		self.path = url
		self.set_path_calls = []
	def get_path(self):
		return self.path
	def set_path(self, path, callback=None):
		self.set_path_calls.append(path)
		if callback:
			callback()
	def move_cursor_home(self):
		pass

@skipUnless(PLATFORM == 'Windows', '.lnk shortcuts are a Windows concept')
class FollowShortcutTest(TestCase):
	def test_visible_only_on_local_shortcuts(self):
		cases = (
			('file://C:/a/x.lnk', True),
			('file://C:/a/x.LNK', True),
			('file://C:/a/x.txt', False),
			('zip://C:/a.zip/x.lnk', False),
			(None, False),
		)
		for url, expected in cases:
			with self.subTest(url=url):
				command = navigation.FollowShortcut(FakePane(url=url))
				self.assertEqual(expected, command.is_visible())
	def test_opens_the_target(self):
		# Any file that certainly exists will do as the target.
		pane = self._follow(target=__file__)
		self.assertEqual(['open_directory'], pane.commands_run)
		self.assertEqual({'url': as_url(__file__)}, pane.args_run)
		self.show_alert.assert_not_called()
	def test_alerts_when_there_is_no_target(self):
		for target in ('', r'C:\does\not\exist\anywhere.exe'):
			with self.subTest(target=target):
				pane = self._follow(target=target)
				self.assertEqual([], pane.commands_run)
				self.show_alert.assert_called_once()
	def _follow(self, target):
		pane = _ArgRecordingPane(url='file://C:/a/x.lnk')
		with patch(
				'core.commands.navigation.shortcut_target', return_value=target
		), patch('core.commands.navigation.show_alert') as self.show_alert:
			navigation.FollowShortcut(pane)()
		return pane

class HistoryTest(TestCase):
	def test_empty_back(self):
		with self.assertRaises(ValueError):
			self._go_back()
	def test_empty_forward(self):
		with self.assertRaises(ValueError):
			self._go_forward()
	def test_single_back(self):
		self._go_to('single item')
		with self.assertRaises(ValueError):
			self._go_back()
	def test_single_forward(self):
		self._go_to('single item')
		with self.assertRaises(ValueError):
			self._go_forward()
	def test_go_back_forward(self):
		self._go_to('a', 'b', 'c')
		self.assertEqual('b', self._go_back())
		self.assertEqual('a', self._go_back())
		self.assertEqual('b', self._go_forward())
		self.assertEqual('c', self._go_forward())
	def test_go_to_after_back(self):
		self._go_to('a', 'b')
		self.assertEqual('a', self._go_back())
		self._go_to('c')
		self.assertEqual(['a', 'c'], self._history._paths)
	def setUp(self):
		super().setUp()
		self._history = History()
	def _go_back(self):
		path = self._history.go_back()
		self._history.path_changed(path)
		return path
	def _go_forward(self):
		path = self._history.go_forward()
		self._history.path_changed(path)
		return path
	def _go_to(self, *paths):
		for path in paths:
			self._history.path_changed(path)

class OnePaneNavigationTest(TestCase):
	def test_open_in_left_or_right_is_hidden_and_noop(self):
		pane = _NavigationPane([])
		pane.window._panes.append(pane)
		for command_type in (navigation.OpenInLeftPane, navigation.OpenInRightPane):
			with self.subTest(command=command_type.__name__):
				command = command_type(pane)
				self.assertFalse(command.is_visible())
				command()
		self.assertEqual([], pane.commands_run)
	def test_show_volumes_out_of_range_uses_current_pane(self):
		pane = _NavigationPane([])
		pane.window._panes.append(pane)
		with patch('core.commands.navigation._get_volumes_url', return_value='drives://'):
			navigation.ShowVolumes(pane)(pane_index=1)
		self.assertEqual(['drives://'], pane.set_path_calls)
