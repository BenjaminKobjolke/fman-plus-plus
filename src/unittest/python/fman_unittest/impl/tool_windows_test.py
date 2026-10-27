"""Tests for minimized task progress windows and their status-bar buttons."""

from fman.impl.tool_windows import ToolWindowOptions, ToolWindows
from PyQt5.QtWidgets import QApplication, QProgressDialog, QStatusBar, QToolButton
from unittest import TestCase


class ToolWindowOptionsTest(TestCase):
	def test_default_task_options_preserve_plugin_behavior(self):
		options = ToolWindowOptions.of(type('Task', (), {}))
		self.assertFalse(options.keeps_focus)
		self.assertFalse(options.minimizable)
		self.assertIsNone(options.icon)

	def test_options_read_task_class_attributes(self):
		icon = object()
		task = type('Task', (), {
			'keeps_focus': True, 'minimizable': True, 'icon': icon
		})
		options = ToolWindowOptions.of(task)
		self.assertTrue(options.keeps_focus)
		self.assertTrue(options.minimizable)
		self.assertIs(icon, options.icon)


class ToolWindowsTest(TestCase):
	def test_minimize_restore_and_remove(self):
		status_bar = QStatusBar()
		windows = ToolWindows(status_bar)
		dialog = QProgressDialog('Copying', 'Cancel', 0, 100)
		windows.register(dialog, True)

		windows.minimize(dialog, 'Copying files')

		self.assertFalse(dialog.isVisible())
		self.assertEqual([(dialog, 'Copying files')], windows.minimized())
		button, = status_bar.findChildren(QToolButton)
		self.assertEqual('Copying files', button.toolTip())
		button.click()
		self.assertTrue(dialog.isVisible())
		self.assertEqual([], windows.minimized())
		self.assertEqual([], status_bar.findChildren(QToolButton))

		windows.minimize(dialog, 'Copying files')
		windows.remove(dialog)
		self.assertEqual([], windows.minimized())
		self.assertEqual([], status_bar.findChildren(QToolButton))

	def test_two_minimized_windows_keep_distinct_titles(self):
		status_bar = QStatusBar()
		windows = ToolWindows(status_bar)
		dialogs = [QProgressDialog('Cancel', 'Cancel', 0, 100)
			for _ in ('Copy', 'Move')]
		for dialog, title in zip(dialogs, ('Copy', 'Move')):
			dialog.setWindowTitle(title)

		for dialog in dialogs:
			windows.register(dialog, True)
			windows.minimize(dialog, dialog.windowTitle())

		self.assertEqual(
			[(dialogs[0], 'Copy'), (dialogs[1], 'Move')], windows.minimized()
		)
		self.assertEqual(
			['Copy', 'Move'],
			[button.toolTip() for button in status_bar.findChildren(QToolButton)]
		)

	def test_visible_minimizable_is_the_most_recently_shown_dialog(self):
		windows = ToolWindows(QStatusBar())
		first = _Dialog()
		second = _Dialog()
		windows.register(first, True)
		windows.register(second, True)
		first.show()
		windows.shown(first)
		second.show()
		windows.shown(second)
		self.app.processEvents()

		self.assertIs(second, windows.visible_minimizable())
		second.hide()
		self.assertIs(first, windows.visible_minimizable())
		first.hide()
		self.assertIsNone(windows.visible_minimizable())

	def test_default_icon_uses_application_style(self):
		status_bar = QStatusBar()
		windows = ToolWindows(status_bar)
		dialog = QProgressDialog('Copying', 'Cancel', 0, 100)
		windows.register(dialog, True)
		windows.minimize(dialog, 'Copying')
		button, = status_bar.findChildren(QToolButton)
		self.assertFalse(button.icon().isNull())

	@classmethod
	def setUpClass(cls):
		cls.app = QApplication.instance() or QApplication([])


class _Dialog:
	minimizable = True

	def __init__(self):
		self._visible = False
		self._shown_at = 0

	def show(self):
		self._visible = True
		self._shown_at += 1

	def hide(self):
		self._visible = False

	def isVisible(self):
		return self._visible

	def shown_at(self):
		return self._shown_at
