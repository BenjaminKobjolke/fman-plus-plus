"""Copy the current item into the same directory under a free name."""
from core.commands.transfer import Copy
from fman.url import basename, dirname, join
import fman
import fman.fs
import os.path
from typing import List, Optional

__all__ = ['DuplicateFile', 'suggest_duplicate_name']


def suggest_duplicate_name(file_url: str) -> str:
	name = basename(file_url)
	stem, extension = os.path.splitext(name)
	try:
		if fman.fs.is_dir(file_url):
			stem, extension = name, ''
	except OSError:
		# The command normally receives an existing selection. Keeping name
		# generation useful for a missing URL also makes it easy to preview.
		pass
	number = 1
	while True:
		candidate = '%s Copy %d%s' % (stem, number, extension)
		if not fman.fs.exists(join(dirname(file_url), candidate)):
			return candidate
		number += 1


class DuplicateFile(Copy):
	aliases = ('Create a duplicate file', 'Copy file here', 'Duplicate file')

	def __call__(self, files: Optional[List[str]] = None,
	             dest_dir: Optional[str] = None) -> None:
		if dest_dir is None:
			dest_dir = self.pane.get_path()
		return super().__call__(files, dest_dir)

	@classmethod
	def _suggest_name(cls, file_url):
		return suggest_duplicate_name(file_url)

	@classmethod
	def _verb(cls):
		return 'copy'
