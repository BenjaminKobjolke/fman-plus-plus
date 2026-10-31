"""Windows notification-area behavior for the main fman window."""

from fman.impl.single_instance import bring_to_front
from PyQt5.QtCore import QEvent, QObject, Qt, QTimer
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon

MINIMIZE_TO_TRAY_SETTING = 'minimize_to_tray'
MINIMIZE_TO_TRAY_ON_MESSAGE = 'Minimize to tray is on.'
MINIMIZE_TO_TRAY_OFF_MESSAGE = 'Minimize to tray is off.'


def should_show_tray_icon(minimize_to_tray, window_hidden):
	return minimize_to_tray or window_hidden


def should_hide_on_minimize(minimize_to_tray):
	return minimize_to_tray


class Tray(QObject):
	def __init__(self, app, main_window, settings):
		super().__init__(main_window)
		self._app = app
		self._main_window = main_window
		self.settings = settings
		self._app.setQuitOnLastWindowClosed(False)
		self._icon = QSystemTrayIcon(main_window.windowIcon(), main_window)
		self._menu = QMenu(main_window)
		show_action = QAction('Show', self._menu)
		show_action.triggered.connect(self.show)
		quit_action = QAction('Quit', self._menu)
		quit_action.triggered.connect(self._app.exit)
		self._menu.addAction(show_action)
		self._menu.addAction(quit_action)
		self._icon.setContextMenu(self._menu)
		self._icon.activated.connect(self._on_activated)
		main_window.installEventFilter(self)
		self._icon.show()
		self._update_icon_visibility()

	def show(self):
		bring_to_front(self._main_window)
		self._update_icon_visibility()

	def hide(self):
		self._main_window.setWindowState(
			self._main_window.windowState() & ~Qt.WindowMinimized
		)
		self._main_window.hide()
		self._update_icon_visibility()

	def toggle(self):
		if self._main_window.isVisible():
			self.hide()
		else:
			self.show()

	def toggle_minimize_to_tray(self):
		if self.settings.get(MINIMIZE_TO_TRAY_SETTING, False):
			self.settings.pop(MINIMIZE_TO_TRAY_SETTING)
			message = MINIMIZE_TO_TRAY_OFF_MESSAGE
		else:
			self.settings[MINIMIZE_TO_TRAY_SETTING] = True
			message = MINIMIZE_TO_TRAY_ON_MESSAGE
		self.settings.flush()
		self._update_icon_visibility()
		return message

	def eventFilter(self, watched, event):
		if watched is self._main_window:
			if event.type() == QEvent.WindowStateChange:
				if (self._main_window.isMinimized()
						and should_hide_on_minimize(
							self.settings.get(MINIMIZE_TO_TRAY_SETTING, False))):
					QTimer.singleShot(0, self.hide)
				else:
					self._update_icon_visibility()
			elif event.type() in (QEvent.Show, QEvent.Hide):
				self._update_icon_visibility()
		return False

	def _on_activated(self, reason):
		if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
			self.show()

	def _update_icon_visibility(self):
		hidden = not self._main_window.isVisible()
		visible = should_show_tray_icon(
			self.settings.get(MINIMIZE_TO_TRAY_SETTING, False), hidden
		)
		self._icon.setVisible(visible)
