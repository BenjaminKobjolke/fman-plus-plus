"""Application-level odds and ends: about, help, quit, and the no-op commands.

`DoNothing` and `none` both exist only to be bound to. fman's binding
sanitizer drops bindings whose command does not exist, so shadowing a shipped
default needs a real command to point at.
"""
from fman import APP_NAME, ApplicationCommand, DATA_DIRECTORY, \
	DirectoryPaneCommand, FMAN_VERSION, links, show_alert
from fman.url import as_url
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

import sys

__all__ = [
	'About', 'DoNothing', 'Help', 'OpenDataDirectory', 'Quit', 'ZenOfFman',
	'none'
]

MAINTAINER = 'Benjamin Kobjolke'
ORIGINAL_AUTHOR = 'Michael Herrmann'

class About(ApplicationCommand):
	def __call__(self):
		show_alert(
			APP_NAME + " version: " + FMAN_VERSION + "\n"
			+ "Maintained by " + MAINTAINER + ".\n"
			+ "Based on fman by " + ORIGINAL_AUTHOR + "."
		)

class Help(ApplicationCommand):

	aliases = ('Help',)

	def __call__(self):
		QDesktopServices.openUrl(QUrl(links.HELP))

class DoNothing(DirectoryPaneCommand):

	"""
	Exists only to be bound to: unbinding a shipped default means shadowing it
	with a higher-priority binding, and fman's sanitizer drops bindings whose
	command doesn't exist. See core/binding_editor.py.
	"""

	aliases = ('Do nothing',)

	def __call__(self):
		pass
	def is_visible(self):
		# Nothing to run from the palette - it is a target, not an action.
		return False

class Quit(ApplicationCommand):

	aliases = ('Quit',)

	def __call__(self):
		sys.exit(0)

class ZenOfFman(ApplicationCommand):
	aliases = ('Zen of fman++',)

	def __call__(self):
		show_alert(
			"The Zen of " + APP_NAME + "\n"
			+ links.ZEN + "\n\n"
			"Looks matter\n"
			"Speed counts\n"
			"Extending must be easy\n"
			"Customisability is important\n"
			"But not at the expense of speed\n"
			"I/O is better asynchronous\n"
			"Updates should be transparent and continuous\n"
			"Don't reinvent the wheel"
		)

class OpenDataDirectory(DirectoryPaneCommand):
	def __call__(self):
		self.pane.set_path(as_url(DATA_DIRECTORY))

class none(DirectoryPaneCommand):
	"""
	Assign key bindings to this command to effectively deactivate them.
	This is a DirectoryPaneCommand because ApplicationCommand currently does not
	support is_visible().
	"""
	def __call__(self):
		pass
	def is_visible(self):
		return False
