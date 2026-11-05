"""Read-only RAR browsing through the bundled 7-Zip executable."""

from core.fs.read_only_archive import _ReadOnly7ZipFileSystem

__all__ = ['RarFileSystem']


class RarFileSystem(_ReadOnly7ZipFileSystem):
	scheme = 'rar://'
	read_only_message = 'RAR archives are read-only.'
