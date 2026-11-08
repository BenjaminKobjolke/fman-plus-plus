"""
Icon sets: where the file list's icons come from.

DEFAULT_ICON_SET means "ask the OS" - the Windows shell, GTK or macOS icon
fman has always used. Any other name is a directory holding a manifest.json
mapping file names, extensions and folder names to icon names, plus an svg/
directory holding those icons. fman bundles one such set, Material; a user
may drop their own into %APPDATA%/fman/Icons/<Name>/.

Deliberately shaped like fman.impl.themes: same list_/load_ pair, same
"later dirs win" rule, and the same promise that a broken file costs you
that one set rather than fman's startup. Which set is active is a theme
property - see docs/THEMES.md.
"""
from glob import escape, glob
from json import load
from os.path import basename, dirname, isfile, join

import re

# The icon set used when neither the user nor the theme asks for one. It has
# no directory: it *is* the absence of a set, so IconProvider keeps asking
# the OS the way it did before icon sets existed.
DEFAULT_ICON_SET = 'System'

# The setting key in %APPDATA%/fman/Local/Settings.json, beside `theme` and
# `window_opacity` and there for the same reason - see themes.THEME_SETTING.
ICON_SET_SETTING = 'icon_set'

_MANIFEST = 'manifest.json'
_SVG_DIR = 'svg'

# The manifest keys fman reads. tools/fetch_material_icons.py writes exactly
# these; a hand-written set only has to fill in the ones it cares about.
_FOLDER_NAMES = 'folderNames'
_FILE_NAMES = 'fileNames'
_FILE_EXTENSIONS = 'fileExtensions'
_DEFAULT_FILE = 'file'
_DEFAULT_FOLDER = 'folder'

# An icon name is pasted into a file path, so it may not be able to leave
# svg/. A user's manifest is as untrusted as their theme file: the same
# spirit as themes._ILLEGAL_IN_COLOR, which stops a color breaking out of
# the QSS rule it lands in.
_ICON_NAME = re.compile(r'^[A-Za-z0-9._-]+$')

# Both separators are rejected on every platform, not just the local one: a
# theme file written on Windows is read on Linux too.
_SEPARATORS = frozenset('/\\')

def list_icon_sets(dirs):
	"""
	Icon set names available in `dirs`, sorted. A set's name is its
	directory name - the same string shown in the command palette and stored
	in the settings, so there is no second place for it to disagree with.
	"""
	# The default is always offered: it needs no directory and must stay
	# reachable even if `dirs` are missing.
	result = {DEFAULT_ICON_SET}
	for dir_ in dirs:
		for path in glob(join(escape(dir_), '*', _MANIFEST)):
			result.add(basename(dirname(path)))
	return sorted(result)

def load_icon_set(name, dirs):
	"""
	Icon set `name` from `dirs`, or None if it does not exist, is unreadable
	or is DEFAULT_ICON_SET. None is the "use the OS icons" answer, so a
	broken set degrades to the behavior fman had before icon sets existed.
	Later dirs win, so a user set shadows a bundled one of the same name.
	Never raises: a broken manifest must not stop fman from starting.
	"""
	if not is_valid_icon_set_name(name) or name == DEFAULT_ICON_SET:
		return None
	result = None
	for dir_ in dirs:
		try:
			with open(join(dir_, name, _MANIFEST), 'r') as f:
				manifest = load(f)
		except (OSError, ValueError):
			continue
		# A manifest is valid JSON without being an object: `[]` and `5`
		# parse fine and would make every lookup below raise.
		if isinstance(manifest, dict):
			result = IconSet(name, join(dir_, name), manifest)
	return result

def is_valid_icon_set_name(value):
	"""
	Whether `value` can name an icon set. The name becomes a directory under
	the icon dirs, so a separator or a `..` would let a theme file point
	load_icon_set at somewhere it has no business reading.
	"""
	return isinstance(value, str) and bool(value) \
		and not _SEPARATORS & set(value) \
		and value.strip('.') != ''

class IconSet:

	"""
	One icon set's manifest: which icon a file or folder gets, and where
	that icon's SVG lives. Holds no Qt objects - IconProvider turns a path
	into a QIcon and caches it, because that is where the cache belongs.
	"""

	def __init__(self, name, dir_, manifest):
		self.name = name
		self._dir = dir_
		self._manifest = manifest

	def icon_file(self, file_name, is_dir):
		"""
		The path of the SVG for `file_name`, or None when this set has no
		usable icon for it - in which case the caller falls back to the OS.
		"""
		return self.icon_path(self.icon_name(file_name, is_dir))

	def icon_name(self, file_name, is_dir):
		"""
		The icon `file_name` maps to, or None if the set names no fallback
		either. Lookups are lower-cased: file names on disk vary in case and
		tools/fetch_material_icons.py lower-cases every manifest key.
		"""
		file_name = file_name.lower()
		if is_dir:
			return self._lookup(_FOLDER_NAMES, file_name) \
				or self._manifest.get(_DEFAULT_FOLDER)
		return self._lookup(_FILE_NAMES, file_name) \
			or self._by_extension(file_name) \
			or self._manifest.get(_DEFAULT_FILE)

	def icon_path(self, icon_name):
		"""
		Where `icon_name`'s SVG lives, or None if there is no such file. A
		manifest naming an icon the set does not ship is not an error: it
		reads as "no icon", the same as a name the manifest never mentions.
		"""
		if not isinstance(icon_name, str) or not _ICON_NAME.match(icon_name):
			return None
		result = join(self._dir, _SVG_DIR, icon_name + '.svg')
		return result if isfile(result) else None

	def _lookup(self, key, file_name):
		section = self._manifest.get(key)
		return section.get(file_name) if isinstance(section, dict) else None

	def _by_extension(self, file_name):
		# Longest suffix first: a manifest has hundreds of multi-dot keys
		# (d.ts, schema.json, xml.dist.sample), so foo.d.ts has to match
		# "d.ts" before it settles for "ts".
		parts = file_name.split('.')
		for i in range(1, len(parts)):
			result = self._lookup(_FILE_EXTENSIONS, '.'.join(parts[i:]))
			if result:
				return result
		return None
