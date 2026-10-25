"""Commands for opening the plugin console in a pane or its own window."""

from core.console import show_console_in_pane, show_console_window
from fman import DirectoryPaneCommand

__all__ = ['ShowConsole', 'ShowConsoleWindow']


class ShowConsole(DirectoryPaneCommand):
	usable_in_viewer = True
	aliases = ('Show console',)

	def __call__(self):
		show_console_in_pane(self.pane)


class ShowConsoleWindow(DirectoryPaneCommand):
	usable_in_viewer = True
	aliases = ('Show console window',)

	def __call__(self):
		show_console_window(self.pane)
