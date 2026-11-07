from fman import load_json, PLATFORM
from fman.impl.model.icon_tint import tint_image, TINT_RENDER_SIZE
from fman.impl.model.overlay_compose import compose_overlay
from fman.impl.model.table import invalidate_icons
from fman.impl.util import filenotfounderror
from fman.url import splitscheme
from functools import lru_cache
from pathlib import Path, PurePosixPath
from PyQt5.QtCore import QFileInfo
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QFileIconProvider

import logging
import sys

_LOG = logging.getLogger(__name__)

# The settings this module reads and the Core plugin writes. Public because
# the plugin imports them from here - the engine never imports the plugin, so
# this module owns the contract and ToggleNetworkIcons /
# ToggleExecutableIcons read the names off it.
SETTINGS_FILE = 'Core Settings.json'
# Opting back in to real per-file icons on network drives.
NETWORK_ICONS_KEY = 'network_file_icons'
# Asking Windows per file can slow very large folders; keep it opt-in.
OVERLAY_ICONS_KEY = 'shell_overlay_icons'
# Opting back out of the icon set for programs and shortcuts, where the OS
# icon says which program it is and a set's generic one does not.
EXECUTABLE_ICONS_KEY = 'os_icons_for_executables'
_EXECUTABLE_SUFFIXES = ('.exe', '.lnk')

# An .ico *is* a picture of itself, and the shell draws that picture. No icon
# set can say more about it, so these never go through one.
_SELF_DEPICTING_SUFFIXES = ('.ico',)

class IconProvider:
	def __init__(
		self, qt_icon_provider, fs, cache_dir, icon_set=None, icon_color=None,
		overlay_source=None
	):
		self._qt_icon_provider = qt_icon_provider
		self._fs = fs
		self._folder_icon = self._get_qt_icon(cache_dir)
		self._cache_dir = cache_dir
		self._cache = {
			f.suffix: self._get_qt_icon(f)
			for f in Path(cache_dir).glob('file*')
		}
		self._icon_set = icon_set
		self._icon_color = icon_color
		self._icon_set_cache = {}
		self._overlay_source = overlay_source
		self._overlay_cache = {}
	def set_icon_set(self, icon_set):
		# Switching theme can switch the set (fman.impl.themes), so this
		# happens while fman is running. The cache is keyed by file path,
		# and two sets give the same path different icons - drop it.
		self._icon_set = icon_set
		self._icon_set_cache = {}
		self._overlay_cache = {}
		invalidate_icons()
	def set_icon_color(self, icon_color):
		# Same story as set_icon_set, and the same cache: one path tinted two
		# colors is two icons, so the color cannot be left out of the key by
		# keeping stale entries around.
		self._icon_color = icon_color
		self._icon_set_cache = {}
		self._overlay_cache = {}
		invalidate_icons()
	def get_icon(self, url):
		set_overlay_icons_enabled = getattr(
			self._qt_icon_provider, 'set_overlay_icons_enabled', None
		)
		if set_overlay_icons_enabled is not None:
			set_overlay_icons_enabled(overlay_icons_enabled())
		scheme, path = splitscheme(url)
		if scheme != 'file://':
			url = self._fs.resolve(url)
			scheme, path = splitscheme(url)
		from_set = self._get_icon_set_icon(url, path)
		if from_set is not None:
			return from_set
		if scheme == 'file://':
			return self._get_file_icon(url, path)
		return self._get_generic_icon(url, path)
	def _get_icon_set_icon(self, url, path):
		"""
		The active icon set's icon for `url`, or None to let the OS answer -
		which is also what happens when no set is active at all.
		"""
		if self._icon_set is None:
			return None
		name = PurePosixPath(path)
		suffix = name.suffix.lower()
		if suffix in _SELF_DEPICTING_SUFFIXES:
			return None
		if suffix in _EXECUTABLE_SUFFIXES and _core_setting(
			EXECUTABLE_ICONS_KEY
		):
			return None
		try:
			is_dir = self._fs.is_dir(url)
		except OSError:
			# Mirrors Model#_load_file, which treats a file it cannot stat as
			# "not a directory" rather than failing the listing. Before icon
			# sets, this path never asked - so it must not start raising now.
			return None
		icon_file = self._icon_set.icon_file(name.name, is_dir)
		if icon_file is None:
			return None
		if icon_file not in self._icon_set_cache:
			self._icon_set_cache[icon_file] = \
				_load_icon(icon_file, self._icon_color)
		icon = self._icon_set_cache[icon_file]
		if not self._should_apply_overlay(url, path):
			return icon
		try:
			overlay_index = self._overlay_source.overlay_index(path)
			if not overlay_index:
				return icon
			cache_key = (icon_file, overlay_index)
			if cache_key not in self._overlay_cache:
				overlay = self._overlay_source.pixmap(overlay_index)
				if overlay is None:
					return icon
				self._overlay_cache[cache_key] = compose_overlay(icon, overlay)
			return self._overlay_cache[cache_key]
		except Exception:
			_LOG.exception('Could not obtain shell overlay for %s', path)
			return icon
	def _should_apply_overlay(self, url, path):
		if self._overlay_source is None or not overlay_icons_enabled():
			return False
		if splitscheme(url)[0] != 'file://':
			return False
		return not _is_network_path(path) or _core_setting(NETWORK_ICONS_KEY)
	def _get_file_icon(self, url, path):
		if _is_network_path(path) and not _core_setting(NETWORK_ICONS_KEY):
			# Asking the Windows shell for the icon of a file on a network share
			# means reading that file over the wire - .exe and .dll icons are
			# embedded in the file itself. One generic icon per extension keeps
			# the listing usable. ToggleNetworkIcons opts back in.
			return self._get_generic_icon(url, path)
		return self._get_qt_icon(path)
	def _get_generic_icon(self, url, path):
		if self._fs.is_dir(url):
			return self._folder_icon
		suffix = PurePosixPath(path).suffix
		if suffix not in self._cache:
			surrogate = Path(self._cache_dir, 'file' + suffix)
			with surrogate.open('w') as f:
				# At least Gnome doesn't display a proper icon unless the file
				# has some contents. So give it some:
				f.write('fman')
			self._cache[suffix] = self._get_qt_icon(surrogate)
		return self._cache[suffix]
	def _get_qt_icon(self, path):
		if not isinstance(path, str):
			path = str(path)
		return self._qt_icon_provider.icon(QFileInfo(path))

class GnomeFileIconProvider(QFileIconProvider):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		try:
			self.Gtk, self.Gio, self.GLib = self._init_pgi()
		except (ImportError, ValueError) as e:
			raise GnomeNotAvailable() from e
		else:
			# Access - and save - this constant here, in the main thread.
			# When we access it from other threads, we would otherwise sometimes
			# get "TypeError: query_info() argument 'flags'(2): Expected
			# 'FileQueryInfoFlags' but got 'FileQueryInfoFlags'".
			self._NOFOLLOW_SYMLINKS = \
				self.Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS
	def _init_pgi(self):
		import pgi
		pgi.install_as_gi()
		import gi
		gi.require_version('Gtk', '3.0')
		try:
			from gi.repository import Gtk, Gio, GLib
		except AttributeError as e:
			if e.args == (
				"'GLib' module has not attribute 'uri_list_extract_uris'",
			):
				# This happens when we run fman from source.
				sys.modules['pgi.overrides.GObject'] = None
				from gi.repository import Gtk, Gio, GLib
			else:
				raise
		# This is required when we use pgi in a PyInstaller-frozen app. See:
		# https://github.com/lazka/pgi/issues/38
		Gtk.init(sys.argv)
		return Gtk, Gio, GLib
	def icon(self, arg):
		result = None
		if isinstance(arg, QFileInfo):
			result = self._icon(arg.absoluteFilePath())
		return result or super().icon(arg)
	def _icon(self, file_path):
		try:
			file_info = self._query_gio_info(
				file_path, 'standard::icon', self._NOFOLLOW_SYMLINKS, None
			)
		except FileNotFoundError:
			raise
		except Exception:
			_LOG.exception("Could not obtain icon for %s", file_path)
		else:
			if file_info:
				icon = file_info.get_icon()
				if icon:
					icon_names = icon.get_names()
					if icon_names:
						return self._load_gtk_icon(icon_names[0])
	def _query_gio_info(self, file_path, *args):
		gio_file = self.Gio.file_new_for_path(file_path)
		try:
			return gio_file.query_info(*args)
		except self.GLib.GError as e:
			if e.message and e.message.endswith('No such file or directory'):
				raise filenotfounderror(file_path)
			else:
				raise
	@lru_cache()
	def _load_gtk_icon(self, name, size=32):
		theme = self.Gtk.IconTheme.get_default()
		if theme:
			icon = theme.lookup_icon(name, size, 0)
			if icon:
				return QIcon(icon.get_filename())

class GnomeNotAvailable(RuntimeError):
	pass

def _is_network_path(path):
	# splitscheme(...) hands us the forward-slash form, so a UNC path
	# arrives as //server/share.
	return PLATFORM == 'Windows' and path.startswith('//')

def _core_setting(key):
	"""
	One of the Core plugin's boolean icon settings. Absent means False - the
	settings file only carries the ones the user has turned on.
	"""
	return load_json(SETTINGS_FILE, default={}).get(key, False)

def overlay_icons_enabled():
	"""Whether Windows shell overlays should be fetched for each file."""
	return PLATFORM == 'Windows' and _core_setting(OVERLAY_ICONS_KEY)

def _load_icon(path, color=None):
	# A seam for the tests, which have no QApplication to build a QIcon in -
	# the same reason IconProvider takes its Qt provider as an argument.
	if color is None:
		return QIcon(path)
	# Tinting trades Qt's SVG engine - which redraws crisply at whatever size
	# the view asks for - for one bitmap at TINT_RENDER_SIZE. That is why it
	# only happens when a theme actually asks for a color, and why the size
	# has headroom over MAX_ICON_SIZE rather than matching it.
	image = QIcon(path).pixmap(TINT_RENDER_SIZE, TINT_RENDER_SIZE).toImage()
	return QIcon(QPixmap.fromImage(tint_image(image, color)))
