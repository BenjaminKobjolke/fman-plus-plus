"""Change the destination of a symbolic link, junction or Windows shortcut."""
from core.commands.util import (
	is_file_url, is_shortcut, set_shortcut_target,
	shortcut_target,
)
from fman import (
	DirectoryPaneCommand, NO, PLATFORM, YES, show_alert, show_input, translate,
)
from fman.fs import notify_file_changed
from fman.localization_keys import (
	LINK_TARGET_FAILED, LINK_TARGET_MISSING_CONFIRM, LINK_TARGET_PROMPT,
)
from fman.url import as_human_readable, basename

import os
import stat

if PLATFORM == 'Windows':
	import pywintypes
	_COM_ERROR = pywintypes.com_error
else:
	_COM_ERROR = OSError

_PROMPT = translate(LINK_TARGET_PROMPT)
_MISSING_CONFIRM = translate(LINK_TARGET_MISSING_CONFIRM)
_FAILED = translate(LINK_TARGET_FAILED)

__all__ = ['EditLinkTarget']


class EditLinkTarget(DirectoryPaneCommand):
	aliases = ('Edit link target',)

	def is_visible(self):
		url = self.pane.get_file_under_cursor()
		if not url or not is_file_url(url):
			return False
		path = as_human_readable(url)
		return os.path.islink(path) or _is_junction(path) or (
			PLATFORM == 'Windows' and is_shortcut(path)
		)

	def __call__(self):
		url = self.pane.get_file_under_cursor()
		if not url or not is_file_url(url):
			return
		path = as_human_readable(url)
		is_link_shortcut = PLATFORM == 'Windows' and is_shortcut(path)
		is_junction = _is_junction(path)
		try:
			if is_link_shortcut:
				current = shortcut_target(path)
			else:
				current = _read_link_target(path)
			name = basename(url)
			target = show_input(_PROMPT % name, current, 0, len(current))
			if target is None or not target.strip() or target == current:
				return
			resolved = _resolve_target(path, target)
			if not os.path.exists(resolved):
				answer = show_alert(
					_MISSING_CONFIRM % target, YES | NO, NO
				)
				if not answer & YES:
					return
			if is_link_shortcut:
				set_shortcut_target(path, resolved)
			else:
				_retarget_link(path, target, resolved, is_junction)
		except (OSError, _COM_ERROR) as error:
			show_alert(_FAILED % (basename(url), error))
			return
		notify_file_changed(url)


def _is_junction(path):
	return hasattr(os.path, 'isjunction') and os.path.isjunction(path)


def _read_link_target(path):
	target = os.readlink(path)
	if target.startswith('\\\\?\\'):
		return target[4:]
	return target


def _resolve_target(path, target):
	if os.path.isabs(target):
		return os.path.normpath(target)
	return os.path.normpath(os.path.join(os.path.dirname(path), target))


def _retarget_link(path, target, resolved, is_junction):
	temporary = _temporary_path(path)
	backup = _temporary_path(path + '.fman-original')
	temporary_created = False
	backup_created = False
	try:
		if is_junction:
			import _winapi
			_winapi.CreateJunction(resolved, temporary)
		else:
			if os.path.exists(resolved):
				target_is_directory = os.path.isdir(resolved)
			else:
				target_is_directory = _old_link_is_directory(path)
			os.symlink(
				target, temporary,
				target_is_directory=target_is_directory
			)
		temporary_created = True
		os.rename(path, backup)
		backup_created = True
		try:
			os.rename(temporary, path)
		except OSError:
			os.rename(backup, path)
			backup_created = False
			raise
		temporary_created = False
		try:
			_remove_link(backup, is_junction)
			backup_created = False
		except OSError:
			try:
				_remove_link(path, is_junction)
				os.rename(backup, path)
				backup_created = False
			except OSError:
				pass
			raise
	finally:
		if temporary_created:
			try:
				_remove_link(temporary, is_junction)
			except OSError:
				pass
		if backup_created and not os.path.lexists(path):
			try:
				os.rename(backup, path)
			except OSError:
				pass


def _remove_link(path, is_junction):
	if is_junction or _is_junction(path) or _old_link_is_directory(path):
		os.rmdir(path)
	else:
		os.unlink(path)


def _old_link_is_directory(path):
	if PLATFORM == 'Windows':
		attributes = getattr(os.lstat(path), 'st_file_attributes', 0)
		return bool(attributes & stat.FILE_ATTRIBUTE_DIRECTORY)
	return False


def _temporary_path(path):
	base = path + '.fman-retarget'
	temporary = base
	index = 1
	while os.path.lexists(temporary):
		temporary = '%s-%s' % (base, index)
		index += 1
	return temporary
