from fman import DirectoryPane, Window
from fman.impl.controller import Controller
from fman.impl.plugins import PluginSupport
from fman.impl.widgets import MainWindow
from weakref import WeakValueDictionary
from unittest import TestCase
from unittest.mock import MagicMock, patch


class WindowRemovePaneTest(TestCase):
	def setUp(self):
		self.widget = MagicMock(spec=MainWindow)
		self.controller = MagicMock(spec=Controller)
		self.window = Window(self.widget, MagicMock())
		self.pane = DirectoryPane(self.window, MagicMock(), MagicMock())
		self.pane._widget._mounted_widget = None
		self.window._panes = [self.pane]

	def test_cannot_remove_last_pane(self):
		with patch('fman._get_controller', return_value=self.controller):
			with self.assertRaisesRegex(ValueError, 'last pane'):
				self.window.remove_pane(self.pane)
		self.controller.unregister_pane.assert_not_called()

	def test_cannot_remove_foreign_pane(self):
		self.window._panes.append(DirectoryPane(self.window, MagicMock(), MagicMock()))
		foreign = DirectoryPane(self.window, MagicMock(), MagicMock())
		with patch('fman._get_controller', return_value=self.controller):
			with self.assertRaises(ValueError):
				self.window.remove_pane(foreign)

	def test_unregisters_and_removes_pane(self):
		other = DirectoryPane(self.window, MagicMock(), MagicMock())
		self.window._panes.append(other)
		with patch('fman._get_controller', return_value=self.controller):
			self.window.remove_pane(self.pane)
		self.assertEqual([other], self.window.get_panes())
		self.controller.unregister_pane.assert_called_once_with(
			self.pane._widget, self.pane
		)
		self.widget.remove_pane.assert_called_once_with(self.pane._widget)

	def test_unmounts_view_before_removing_pane(self):
		other = DirectoryPane(self.window, MagicMock(), MagicMock())
		self.window._panes.append(other)
		self.pane._widget._mounted_widget = object()
		self.pane.unmount_widget = MagicMock()
		with patch('fman._get_controller', return_value=self.controller):
			self.window.remove_pane(self.pane)
		self.pane.unmount_widget.assert_called_once()


class UnregisterPaneTest(TestCase):
	def test_plugin_support_unregisters_pane(self):
		support = PluginSupport.__new__(PluginSupport)
		pane = DirectoryPane(None, MagicMock(), MagicMock())
		support._panes = [pane, object()]
		support.unregister_pane(pane)
		self.assertNotIn(pane, support.get_panes())

	def test_controller_unregisters_pane(self):
		controller = Controller.__new__(Controller)
		controller._plugin_support = MagicMock(spec=PluginSupport)
		pane_widget = MagicMock()
		pane = DirectoryPane(None, MagicMock(), MagicMock())
		controller._panes = WeakValueDictionary({pane_widget: pane})
		controller.unregister_pane(pane_widget, pane)
		self.assertNotIn(pane_widget, controller._panes)
		controller._plugin_support.unregister_pane.assert_called_once_with(pane)
