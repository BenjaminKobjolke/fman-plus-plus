from core.plugin_list import PluginListEntry, PluginOs, PluginSource
from core.plugin_sync_dialog import PluginSyncDialog
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from unittest import TestCase


class PluginSyncDialogTest(TestCase):
	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])

	def test_entries_show_source_version_and_other_system_and_default_unchecked(self):
		local = _entry('Local', PluginOs.WINDOWS)
		remote = _entry('Remote', PluginOs.MAC)
		dialog = PluginSyncDialog([local, remote], PluginOs.WINDOWS)
		self.addCleanup(dialog.deleteLater)

		local_item = dialog._list.item(0)
		remote_item = dialog._list.item(1)
		self.assertIn('Local', local_item.text())
		self.assertIn('github', local_item.text())
		self.assertIn('v1', local_item.text())
		self.assertEqual(Qt.Checked, local_item.checkState())
		self.assertIn('(installed on Mac)', remote_item.text())
		self.assertEqual(Qt.Unchecked, remote_item.checkState())

	def test_selected_entries_returns_checked_rows(self):
		entries = [_entry('One'), _entry('Two')]
		dialog = PluginSyncDialog(entries, PluginOs.WINDOWS)
		self.addCleanup(dialog.deleteLater)
		dialog._list.item(1).setCheckState(Qt.Unchecked)
		self.assertEqual((entries[0],), dialog.selected_entries())


def _entry(name, os=PluginOs.WINDOWS):
	return PluginListEntry(
		name, PluginSource.GITHUB, 'https://github.com/example/' + name,
		'v1', os, '2.1.4'
	)
