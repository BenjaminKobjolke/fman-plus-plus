from fman.impl.view.pane_mount import get_colors, mount_widget, unmount_widget
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication
from unittest import TestCase
from unittest.mock import MagicMock, patch

# unmount_widget is decorated with @run_in_main_thread, which needs a
# QApplication to exist (even though it never enters its event loop) - same
# reason core/tests/commands/test_pane_view.py creates one.
_APP = QApplication.instance() or QApplication([])

def _pane_widget():
	# A stand-in for DirectoryPaneWidget (impl/widgets.py:66). Only the three
	# things pane_mount touches are real: the layout, the file view and the
	# _mounted_widget slot declared in DirectoryPaneWidget.__init__.
	widget = MagicMock()
	widget._mounted_widget = None
	return widget

def _pane(widget, others=()):
	pane = MagicMock()
	pane._widget = widget
	pane.window.get_panes.return_value = [pane] + list(others)
	return pane

class GetColorsTest(TestCase):

	"""
	The pane's live colors, so a mounted widget matches whatever theme is
	active rather than hardcoding a palette.
	"""

	def test_reads_base_and_text_from_the_file_view(self):
		widget = _pane_widget()
		palette = QPalette()
		palette.setColor(QPalette.Base, QColor('#001206'))
		palette.setColor(QPalette.Text, QColor('#00b62e'))
		widget._file_view.palette.return_value = palette
		self.assertEqual(('#001206', '#00b62e'), get_colors(widget))

class MountWidgetTest(TestCase):

	def setUp(self):
		self.widget = _pane_widget()
		self.widget.layout.return_value.count.return_value = 1
		self.pane = _pane(self.widget)
		self.view = MagicMock()

	def test_adds_the_view_to_the_pane_layout(self):
		with patch('fman.impl.view.pane_mount.QTimer'):
			mount_widget(self.pane, self.widget, self.view)
		self.widget.layout().insertWidget.assert_called_once_with(0, self.view)

	def test_hides_the_file_list(self):
		with patch('fman.impl.view.pane_mount.QTimer'):
			mount_widget(self.pane, self.widget, self.view)
		self.widget._file_view.setVisible.assert_called_once_with(False)

	def test_records_the_view_on_the_pane_widget(self):
		with patch('fman.impl.view.pane_mount.QTimer'):
			mount_widget(self.pane, self.widget, self.view)
		self.assertIs(self.view, self.widget._mounted_widget)

	def test_repoints_the_focus_proxy_at_the_view(self):
		# switch_panes() focuses the pane widget, which follows its proxy.
		# Without this, tabbing back would land on the hidden file list.
		with patch('fman.impl.view.pane_mount.QTimer'):
			mount_widget(self.pane, self.widget, self.view)
		self.widget.setFocusProxy.assert_called_once_with(self.view)

	def test_focuses_the_view_on_the_next_tick(self):
		# Deferred, because the command palette restores focus to the file
		# view as it closes - grabbing focus now would be clobbered by it.
		with patch('fman.impl.view.pane_mount.QTimer') as timer:
			mount_widget(self.pane, self.widget, self.view)
		timer.singleShot.assert_called_once_with(0, self.view.setFocus)

	def test_without_focus_refocuses_the_other_pane_instead(self):
		# Mounting into the *other* pane: keep the caller's pane focused so
		# browsing continues there. Mounting still blurs it, so re-focus it.
		source = MagicMock()
		pane = _pane(self.widget, others=[source])
		with patch('fman.impl.view.pane_mount.QTimer') as timer:
			mount_widget(pane, self.widget, self.view, focus=False)
		timer.singleShot.assert_called_once_with(0, source.focus)

	def test_still_repoints_the_proxy_when_not_focusing(self):
		# So tabbing into this pane later lands on the view, not the hidden
		# file list.
		pane = _pane(self.widget, others=[MagicMock()])
		with patch('fman.impl.view.pane_mount.QTimer'):
			mount_widget(pane, self.widget, self.view, focus=False)
		self.widget.setFocusProxy.assert_called_once_with(self.view)

class UnmountWidgetTest(TestCase):

	def setUp(self):
		self.widget = _pane_widget()
		self.view = MagicMock()
		self.widget._mounted_widget = self.view

	def test_removes_the_view_from_the_layout(self):
		unmount_widget(self.widget)
		self.widget.layout().removeWidget.assert_called_once_with(self.view)

	def test_deletes_the_view(self):
		unmount_widget(self.widget)
		self.view.deleteLater.assert_called_once_with()

	def test_clears_the_record(self):
		unmount_widget(self.widget)
		self.assertIsNone(self.widget._mounted_widget)

	def test_restores_the_file_list_and_its_focus_proxy(self):
		unmount_widget(self.widget)
		self.widget.setFocusProxy.assert_called_once_with(self.widget._file_view)
		self.widget._file_view.setVisible.assert_called_once_with(True)
		self.widget._file_view.setFocus.assert_called_once_with()

	def test_restores_the_proxy_before_the_file_list_takes_focus(self):
		# Order matters: the file view must not reclaim focus while the proxy
		# still points at the widget being deleted.
		calls = []
		self.widget.setFocusProxy.side_effect = \
			lambda *_: calls.append('proxy')
		self.widget._file_view.setFocus.side_effect = \
			lambda *_: calls.append('focus')
		unmount_widget(self.widget)
		self.assertEqual(['proxy', 'focus'], calls)

	def test_does_nothing_when_no_widget_is_mounted(self):
		self.widget._mounted_widget = None
		unmount_widget(self.widget)
		self.widget.layout().removeWidget.assert_not_called()
		self.widget._file_view.setVisible.assert_not_called()
