"""Commands for creating empty files without opening an editor."""
import os
from core.commands.util import _fs_implements, create_as_admin
from fman import DirectoryPaneCommand, show_alert, show_input
from fman.fs import exists, is_dir, touch
from fman.url import as_human_readable, join, splitscheme
# Use os.path.basename on the name part of a URL, matching the former
# CreateAndEditFile implementation.
from os.path import basename

__all__ = ['NewEmptyFile']


def prompt_for_new_file(pane, caption):
	file_under_cursor = pane.get_file_under_cursor()
	default_name = ''
	if file_under_cursor:
		try:
			file_is_dir = is_dir(file_under_cursor)
		except OSError:
			file_is_dir = False
		if not file_is_dir:
			default_name = basename(file_under_cursor)
	file_name = show_input(
		caption, default_name,
		selection_end=_find_extension_start(default_name)
	)
	if not file_name:
		return None
	return join(pane.get_path(), file_name)


def create_file_if_missing(pane, file_url, unsupported_message):
	if exists(file_url):
		return False
	try:
		touch(file_url)
	except PermissionError as error:
		if not create_as_admin(file_url, is_dir=False, error=error):
			return None
	except NotImplementedError:
		show_alert(unsupported_message)
		return None
	except OSError as error:
		show_alert(
			'Could not create %s: %s' % (as_human_readable(file_url), error)
		)
		return None
	return True


class NewEmptyFile(DirectoryPaneCommand):
	aliases = ('New empty file', 'Create empty file')

	def __call__(self):
		file_url = prompt_for_new_file(
			self.pane, 'Enter file name to create:'
		)
		if file_url is None:
			return
		if create_file_if_missing(
			self.pane, file_url,
			'Creating an empty file is not supported here.'
		) is not True:
			return
		try:
			self.pane.place_cursor_at(file_url)
		except ValueError:
			# Hidden files are omitted from the pane's current listing.
			pass

	def is_visible(self):
		scheme = splitscheme(self.pane.get_path())[0]
		return _fs_implements(scheme, 'touch')


def _find_extension_start(file_name, start=0):
	for dual_extension in ('.pkg.tar.xz', '.tar.xz', '.tar.gz'):
		if file_name.endswith(dual_extension):
			return len(file_name) - len(dual_extension)
	try:
		return file_name.rindex('.', start)
	except ValueError:
		return None


def get_dest_suggestion(dst_url):
	scheme = splitscheme(dst_url)[0]
	if scheme == 'file://':
		sep = os.sep
		suggested_dst = as_human_readable(dst_url)
		offset = 0
	else:
		sep = '/'
		suggested_dst = dst_url
		offset = len(scheme)
	try:
		last_sep = suggested_dst.rindex(sep, offset)
	except ValueError:
		selection_start = offset
	else:
		selection_start = last_sep + 1
	selection_end = _find_extension_start(suggested_dst, selection_start)
	return suggested_dst, selection_start, selection_end
