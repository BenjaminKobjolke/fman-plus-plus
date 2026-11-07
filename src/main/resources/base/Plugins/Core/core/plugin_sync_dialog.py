"""Checklist of plugins found in another fman account session."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
	QApplication, QDialog, QDialogButtonBox, QLabel, QListWidget,
	QListWidgetItem, QVBoxLayout,
)


class PluginSyncDialog(QDialog):
	def __init__(self, entries, this_os, parent=None):
		super().__init__(parent or QApplication.activeWindow())
		self.setWindowTitle('Plugins from your fman account')
		layout = QVBoxLayout(self)
		layout.addWidget(QLabel(
			'Select plugins to install at their saved versions:', self
		))
		self._list = QListWidget(self)
		for entry in entries:
			text = '%s — %s %s @ %s' % (
				entry.name, entry.source.value, entry.location, entry.version
			)
			if entry.os != this_os:
				text += ' (installed on %s)' % entry.os.value
			item = QListWidgetItem(text, self._list)
			item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
			item.setCheckState(
				Qt.Checked if entry.os == this_os else Qt.Unchecked
			)
			item.setData(Qt.UserRole, entry)
		layout.addWidget(self._list)
		buttons = QDialogButtonBox(
			QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
		)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

	def selected_entries(self):
		return tuple(
			self._list.item(index).data(Qt.UserRole)
			for index in range(self._list.count())
			if self._list.item(index).checkState() == Qt.Checked
		)
