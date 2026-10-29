"""Use Windows' SMB connections so every fman file operation keeps working."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from fman.url import as_url
from win32netcon import (
	CONNECT_INTERACTIVE, CONNECT_UPDATE_PROFILE, RESOURCE_CONNECTED,
	RESOURCETYPE_DISK,
)
from win32wnet import (
	NETRESOURCE, WNetAddConnection3, WNetCancelConnection2,
	WNetEnumResource, WNetOpenEnum, error as WNetError,
)

ERROR_CANCELLED = 1223
ERROR_OPEN_FILES = 2401
ERROR_DEVICE_IN_USE = 2404
SMB_SCHEME = 'smb://'


@dataclass(frozen=True)
class ShareAddress:
	server: str
	share: str = ''
	subpath: str = ''

	@property
	def share_unc(self) -> str:
		return '\\\\' + self.server + ('\\' + self.share if self.share else '')

	def as_fman_url(self) -> str:
		if not self.share:
			return 'network://' + self.server
		path = self.share_unc
		if self.subpath:
			path += '\\' + self.subpath.replace('/', '\\')
		return as_url(path)


def parse_share_address(text: str) -> ShareAddress | None:
	"""Parse an SMB URL or UNC path, returning None for local paths."""
	text = text.strip().rstrip('\\/')
	if text.lower().startswith(SMB_SCHEME):
		parsed = urlsplit(text)
		if (
			not parsed.netloc or parsed.username or parsed.password
			or parsed.query or parsed.fragment
		):
			return None
		server = parsed.netloc
		path = parsed.path.strip('/')
	else:
		if not text.startswith(('\\\\', '//')):
			return None
		parts = (
			text.replace('/', '\\').lstrip('\\').split('\\')
		)
		server, path = parts[0], '/'.join(parts[1:])
	if not server or any(char in server for char in '\\/:'):
		return None
	parts = [part for part in path.replace('\\', '/').split('/') if part]
	return ShareAddress(server, parts[0] if parts else '', '/'.join(parts[1:]))


def connect_share(
		share_unc: str, drive_letter: str | None = None,
		owner_hwnd: int | None = None
) -> bool:
	resource = NETRESOURCE()
	resource.dwType = RESOURCETYPE_DISK
	resource.lpRemoteName = share_unc
	resource.lpLocalName = drive_letter + ':' if drive_letter else None
	flags = CONNECT_INTERACTIVE
	if drive_letter:
		flags |= CONNECT_UPDATE_PROFILE
	try:
		WNetAddConnection3(owner_hwnd, resource, None, None, flags)
	except WNetError as error:
		if _error_code(error) == ERROR_CANCELLED:
			return False
		raise
	return True


@dataclass(frozen=True)
class ShareConnection:
	local_name: str
	remote_name: str

	@property
	def name(self) -> str:
		return self.local_name or self.remote_name

	@property
	def title(self) -> str:
		if self.local_name:
			return self.local_name + '  ' + self.remote_name
		return self.remote_name


def list_connections() -> list[ShareConnection]:
	enum = WNetOpenEnum(RESOURCE_CONNECTED, RESOURCETYPE_DISK, 0, None)
	try:
		resources = WNetEnumResource(enum, 0)
		return [
			ShareConnection(resource.lpLocalName or '', resource.lpRemoteName)
			for resource in resources
		]
	finally:
		enum.Close()


def disconnect(connection: ShareConnection) -> None:
	flags = CONNECT_UPDATE_PROFILE if connection.local_name else 0
	WNetCancelConnection2(connection.name, flags, False)


def describe_wnet_error(error: WNetError) -> str:
	message = getattr(error, 'strerror', None) or str(error)
	if _error_code(error) in (ERROR_OPEN_FILES, ERROR_DEVICE_IN_USE):
		message += '\nFiles on it are still open. Close them and try again.'
	return message


def _error_code(error: WNetError) -> int | None:
	return getattr(error, 'winerror', error.args[0] if error.args else None)
