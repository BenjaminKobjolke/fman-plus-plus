"""Minimization support for task progress dialogs."""

from dataclasses import dataclass
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QStyle, QToolButton


@dataclass(frozen=True)
class ToolWindowOptions:
	keeps_focus: bool = False
	minimizable: bool = False
	icon: object = None

	@classmethod
	def of(cls, task):
		return cls(
			keeps_focus=getattr(task, 'keeps_focus', False),
			minimizable=getattr(task, 'minimizable', False),
			icon=getattr(task, 'icon', None)
		)


class ToolWindows:
	"""Tracks active progress dialogs and their minimized status buttons."""

	def __init__(self, status_bar):
		self._status_bar = status_bar
		self._windows = {}
		self._next_shown = 0

	def register(self, dialog, minimizable):
		if minimizable:
			self._windows[dialog] = {'shown': 0, 'minimized': None}

	def shown(self, dialog):
		window = self._windows.get(dialog)
		if window is not None:
			self._next_shown += 1
			window['shown'] = self._next_shown

	def minimize(self, dialog, title, icon=None):
		window = self._windows[dialog]
		if window['minimized'] is not None:
			return
		button = QToolButton(self._status_bar)
		button.setToolButtonStyle(Qt.ToolButtonIconOnly)
		button.setAutoRaise(True)
		button.setToolTip(title)
		style = QApplication.style()
		button.setIcon(icon if icon is not None else style.standardIcon(
			QStyle.SP_FileDialogDetailedView
		))
		button.clicked.connect(lambda: self.restore(dialog))
		window['minimized'] = (title, button)
		self._status_bar.addPermanentWidget(button)
		dialog.hide()

	def restore(self, dialog):
		window = self._windows.get(dialog)
		if window is None or window['minimized'] is None:
			return
		self._remove_button(window)
		dialog.show()

	def remove(self, dialog):
		window = self._windows.pop(dialog, None)
		if window is not None:
			self._remove_button(window)

	def minimized(self):
		return [
			(dialog, window['minimized'][0])
			for dialog, window in self._windows.items()
			if window['minimized'] is not None
		]

	def visible_minimizable(self):
		visible = [
			(dialog, window['shown'])
			for dialog, window in self._windows.items()
			if dialog.isVisible()
		]
		return max(visible, key=lambda item: item[1])[0] if visible else None

	def _remove_button(self, window):
		if window['minimized'] is None:
			return
		button = window['minimized'][1]
		self._status_bar.removeWidget(button)
		button.setParent(None)
		button.deleteLater()
		window['minimized'] = None
