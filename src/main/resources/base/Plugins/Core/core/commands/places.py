"""Command-palette entries for the directories that are otherwise hard to reach.

GoTo (Ctrl+P) can open any of these - but only if you already know the path.
It suggests the non-hidden subdirs of your home directory
(`GoTo._get_default_paths`), which leaves out exactly the interesting ones:
AppData, ProgramData and %TEMP% are hidden, and Desktop / Documents /
Downloads move out from under `~` as soon as OneDrive takes them over. Each
command here gives one such place a name you can find by typing it.
"""

from core.commands.util import get_desktop, get_documents, get_downloads, \
	get_home, get_program_files, get_program_files_x86
from fman import DATA_DIRECTORY, DirectoryPaneCommand, PLATFORM
from fman.url import as_url
from os.path import expanduser
from tempfile import gettempdir

import os

__all__ = [
	'GoHome', 'GoToAppData', 'GoToDesktop', 'GoToDocuments', 'GoToDownloads',
	'GoToPluginsDirectory', 'GoToTemp'
]

def _env_dir(name):
	# None (not '') so that is_visible() below hides a command whose
	# destination this machine doesn't have.
	return os.environ.get(name) or None

class _GoToDirectory(DirectoryPaneCommand):

	"""Base for the commands below. Private, so `import *` never registers it."""

	def get_directory(self):
		raise NotImplementedError()
	def is_visible(self):
		directory = self.get_directory()
		return bool(directory) and os.path.isdir(directory)
	def __call__(self):
		directory = self.get_directory()
		# OpenDirectory, like GoTo, reports a vanished directory gracefully.
		self.pane.run_command('open_directory', {'url': as_url(directory)})

class GoHome(_GoToDirectory):

	aliases = ('Go home',)

	def get_directory(self):
		return get_home()

class GoToDesktop(_GoToDirectory):

	aliases = ('Go to desktop',)

	def get_directory(self):
		return get_desktop()

class GoToDocuments(_GoToDirectory):

	aliases = ('Go to documents',)

	def get_directory(self):
		return get_documents()

class GoToDownloads(_GoToDirectory):

	aliases = ('Go to downloads',)

	def get_directory(self):
		return get_downloads()

class GoToAppData(_GoToDirectory):

	aliases = ('Go to AppData',)

	def get_directory(self):
		if PLATFORM == 'Windows':
			return _env_dir('APPDATA')
		if PLATFORM == 'Mac':
			return expanduser('~/Library/Application Support')
		return _env_dir('XDG_CONFIG_HOME') or expanduser('~/.config')

class GoToPluginsDirectory(_GoToDirectory):

	aliases = ('Go to fman++ plugins directory',)

	def get_directory(self):
		return os.path.join(DATA_DIRECTORY, 'Plugins')

class GoToTemp(_GoToDirectory):

	aliases = ('Go to temp',)

	def get_directory(self):
		return gettempdir()

if PLATFORM == 'Windows':

	__all__ += [
		'GoToLocalAppData', 'GoToProgramData', 'GoToProgramFiles',
		'GoToProgramFilesX86'
	]

	class GoToLocalAppData(_GoToDirectory):

		aliases = ('Go to local AppData',)

		def get_directory(self):
			return _env_dir('LOCALAPPDATA')

	class GoToProgramData(_GoToDirectory):

		aliases = ('Go to ProgramData',)

		def get_directory(self):
			return _env_dir('PROGRAMDATA')

	class GoToProgramFiles(_GoToDirectory):

		aliases = ('Go to Program Files',)

		def get_directory(self):
			return get_program_files()

	class GoToProgramFilesX86(_GoToDirectory):

		aliases = ('Go to Program Files (x86)',)

		def get_directory(self):
			# get_program_files_x86() reads %PROGRAMFILES%, which only points
			# at the x86 directory inside a 32-bit process - in a 64-bit one it
			# is the same as %PROGRAMW6432% and this row would duplicate
			# "Go to Program Files". ProgramFiles(x86) is right either way.
			return _env_dir('ProgramFiles(x86)') or get_program_files_x86()
