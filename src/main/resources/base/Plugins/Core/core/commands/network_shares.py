"""Connect to Windows network shares while leaving SMB access to Windows."""

from fman import PLATFORM, DirectoryPaneCommand, show_alert

__all__ = []

if PLATFORM == 'Windows':
	__all__ += ['ConnectNetworkShare', 'DisconnectNetworkShare']
	import ctypes
	import re
	import win32gui
	from enum import Enum
	from win32wnet import error as WNetError
	from core.fs.local.windows.shares import (
		connect_share, describe_wnet_error,
		disconnect, list_connections, parse_share_address,
	)
	from fman import QuicksearchItem, show_prompt, show_quicksearch
	from fman.url import as_human_readable, as_url

	class ShareLogin(Enum):
		NOT_A_SHARE = 0
		CONNECTED = 1
		CANCELLED = 2
		FAILED = 3

	def log_in_to_share(url: str) -> ShareLogin:
		"""Ask Windows to connect a protected UNC share, if this is one."""
		address = parse_share_address(as_human_readable(url))
		if address is None or not address.share:
			return ShareLogin.NOT_A_SHARE
		try:
			connected = connect_share(
				address.share_unc, owner_hwnd=win32gui.GetForegroundWindow()
			)
		except WNetError as error:
			show_alert(
				'Could not connect to "%s": %s' % (
					address.share_unc, describe_wnet_error(error)
				)
			)
			return ShareLogin.FAILED
		return ShareLogin.CONNECTED if connected else ShareLogin.CANCELLED

	class ConnectNetworkShare(DirectoryPaneCommand):
		aliases = ('Connect to network share',)

		def __call__(self):
			current = parse_share_address(
				as_human_readable(self.pane.get_path())
			)
			default = current.share_unc if current and current.share else 'smb://'
			text, accepted = show_prompt('Network share address:', default)
			if not accepted or not text:
				return
			address = parse_share_address(text)
			if address is None or not address.share:
				show_alert('Enter a share, for example smb://server/share.')
				return
			letter, accepted = show_prompt('Drive letter (leave empty for none):')
			if not accepted:
				return
			letter = letter.strip().upper()
			if letter.endswith(':'):
				letter = letter[:-1]
			if letter and not re.fullmatch('[A-Z]', letter):
				show_alert('Enter one drive letter, such as Z, or leave it empty.')
				return
			if letter and _drive_letter_in_use(letter):
				show_alert('Drive letter %s: is already in use.' % letter)
				return
			try:
				connected = connect_share(
					address.share_unc, letter or None,
					win32gui.GetForegroundWindow()
				)
			except WNetError as error:
				show_alert(
					'Could not connect to "%s": %s' % (
						address.share_unc, describe_wnet_error(error)
					)
				)
				return
			if connected:
				url = as_url(letter + ':\\') if letter else address.as_fman_url()
				self.pane.run_command('open_directory', {'url': url})

	class DisconnectNetworkShare(DirectoryPaneCommand):
		aliases = ('Disconnect network share',)

		def __call__(self):
			connections = list_connections()
			if not connections:
				show_alert('No network shares are connected.')
				return
			pane_address = parse_share_address(
				as_human_readable(self.pane.get_path())
			)
			current = _connection_for_path(
				connections, self.pane.get_path(), pane_address
			)
			selected = connections.index(current) if current in connections else 0
			def get_items(query):
				return [
					QuicksearchItem(connection, connection.title)
					for connection in connections
					if query.lower() in connection.title.lower()
				]
			result = show_quicksearch(get_items, item=selected)
			if not result:
				return
			connection = result[1]
			try:
				disconnect(connection)
			except WNetError as error:
				show_alert(
					'Could not disconnect "%s": %s' % (
						connection.name, describe_wnet_error(error)
					)
				)
				return
			if _connection_for_path([connection], self.pane.get_path(), pane_address):
				self.pane.set_path('drives://')

	def _drive_letter_in_use(letter):
		mask = ctypes.windll.kernel32.GetLogicalDrives()
		return bool(mask & (1 << (ord(letter) - ord('A'))))

	def _connection_for_path(connections, path, address):
		if address and address.share:
			for connection in connections:
				if connection.remote_name.lower() == address.share_unc.lower():
					return connection
		local_path = as_human_readable(path)
		if re.match('^[A-Za-z]:\\\\', local_path):
			letter = local_path[:2]
			for connection in connections:
				if connection.local_name.lower() == letter.lower():
					return connection
		return None
