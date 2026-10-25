"""fman's built-in commands, grouped one module per concern.

Nothing is defined here any more: this file only re-exports. fman's plugin
loader (src/main/python/fman/impl/plugins/plugin.py) discovers commands by
walking `dir(core)` for classes, so a command counts as registered exactly
when it is reachable as an attribute of the top-level `core` package - which
is what `core/__init__.py`'s `from core.commands import *` plus the star
imports below arrange. Which module a command is defined in is invisible to
the loader, to key bindings and to 'Command Titles.json'; the class name is
not - that is where the command name comes from.

`import *` skips underscore-prefixed names, so a helper one module borrows
from another has to be imported explicitly, by that module, from its owner.
core/commands/util.py holds the ones several modules need at once, because
none of those modules may import a sibling that imports it back.

That, plus each submodule's __all__, means the star imports alone re-export
only command classes - where this used to be one flat module defining every
helper as well. `__getattr__` below closes that gap for plugins.
"""
from importlib import import_module as _import_module

_COMMAND_MODULES = (
	'app', 'archives', 'clipboard', 'columns', 'deletion', 'drag_to_app',
	'editor', 'external', 'file_properties', 'goto', 'hidden_files',
	'navigation', 'open_with', 'opening', 'pack', 'palette', 'pane_view',
	'places', 'plugins', 'release_notes', 'rename', 'theme', 'transfer',
	'undo', 'updates', 'window'
)
__all__ = []
for _module_name in _COMMAND_MODULES:
	_module = _import_module('.' + _module_name, __name__)
	_module_names = getattr(
		_module, '__all__',
		(name for name in vars(_module) if not name.startswith('_'))
	)
	for _name in _module_names:
		globals()[_name] = getattr(_module, _name)
		__all__.append(_name)

def __getattr__(name):
	# Third-party plugins were written against the flat core/commands.py and
	# import names the star imports do not re-export: private helpers such as
	# _open_local_files, public ones a submodule's __all__ narrows away, and
	# incidental imports like `os`. Splitting this package was our change, so
	# resolve those from the submodules instead of breaking the plugin. No
	# submodule defines a private name another one also defines, so the first
	# match is the only match. The submodules are read from the package
	# directory rather than listed here: a list would be the star imports
	# above written a second time, minus the two modules they leave out
	# (explorer_properties holds no commands, util only helpers), and the two
	# would drift apart the next time this package is split further.
	if name.startswith('__'):
		# Dunders are Python's own lookups (__path__, __all__, copy/pickle
		# protocols), never a plugin's; answering them from a submodule would
		# hand out the wrong module's internals.
		raise AttributeError(name)
	from pkgutil import iter_modules
	for submodule in iter_modules(__spec__.submodule_search_locations):
		try:
			return getattr(
				_import_module('.' + submodule.name, __name__), name
			)
		except AttributeError:
			continue
	raise AttributeError(
		"module %r has no attribute %r" % (__name__, name)
	)
