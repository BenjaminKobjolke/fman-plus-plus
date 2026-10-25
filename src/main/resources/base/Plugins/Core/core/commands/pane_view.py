"""Pane-level view state: which panes are visible, and how big their text is.

The font-size cluster keeps `_base_pane_font_size` next to every function that
reads or writes it - it is the theme's own pane font, readable only from a
live view that has not been given an override stylesheet yet, so a second copy
of the global in another module would silently break the icon scaling that
derives from it (see docs/ICONS.md).
"""
from core.commands.util import get_opposite_pane
from core.commands.hidden_files import _forget_pane_info
from core.font_size import change_font_size, effective_font_size, \
	get_saved_font_size, reset_font_size
from fman import DirectoryPaneCommand, DirectoryPaneListener
# Not in fman's __all__, so a star import would not bring these in - the same
# reason commands/theme.py names the icon functions explicitly.
from fman import set_icon_scale, set_palette_font_scale
from fman.impl.util.qt.thread import run_in_main_thread

__all__ = [
	'AddPane', 'DecreasePaneFontSize', 'IncreasePaneFontSize', 'InitPaneFontSize',
	'Reload', 'ResetPaneFontSize', 'ShowAllPanes', 'ShowOnlyActivePane',
	'SwitchPanes', 'RemovePane'
]

class Reload(DirectoryPaneCommand):

	aliases = ('Reload',)

	def __call__(self):
		self.pane.reload()

class SwitchPanes(DirectoryPaneCommand):
	def __call__(self, pane_index=None):
		if pane_index is None:
			pane = get_opposite_pane(self.pane)
		else:
			panes = self.pane.window.get_panes()
			if pane_index >= len(panes):
				return
			pane = panes[pane_index]
		# In single-pane mode (ShowOnlyActivePane) the other pane is hidden;
		# focusing it would move the cursor into a pane the user can't see.
		if not pane._widget.isVisible():
			return
		pane.focus()

class AddPane(DirectoryPaneCommand):
	usable_in_viewer = True
	def is_visible(self):
		return not _any_pane_hidden(self.pane.window.get_panes())
	def __call__(self):
		new_pane = self.pane.window.add_pane()
		new_pane.set_path(self.pane.get_path(), callback=new_pane.focus)

class RemovePane(DirectoryPaneCommand):
	usable_in_viewer = True
	def is_visible(self):
		panes = self.pane.window.get_panes()
		return len(panes) > 1 and not _any_pane_hidden(panes)
	def __call__(self):
		panes = self.pane.window.get_panes()
		if len(panes) < 2:
			return
		neighbour = get_opposite_pane(self.pane)
		_forget_pane_info(self.pane)
		self.pane.window.remove_pane(self.pane)
		neighbour.focus()

def _any_pane_hidden(panes):
	return any(not pane._widget.isVisible() for pane in panes)

class ShowOnlyActivePane(DirectoryPaneCommand):
	usable_in_viewer = True

	def is_visible(self):
		panes = self.pane.window.get_panes()
		return len(panes) > 1 and not _any_pane_hidden(panes)
	@run_in_main_thread
	def __call__(self):
		for pane in self.pane.window.get_panes():
			pane._widget.setVisible(pane is self.pane)
		self.pane.focus()

class ShowAllPanes(DirectoryPaneCommand):
	usable_in_viewer = True

	def is_visible(self):
		return _any_pane_hidden(self.pane.window.get_panes())
	@run_in_main_thread
	def __call__(self):
		for pane in self.pane.window.get_panes():
			pane._widget.setVisible(True)
		self.pane.focus()

_SETTING_KEY = 'pane_font_size'
# The read/clamp/save/apply algorithm lives in core/font_size (imported
# above) so the text viewer's own zoom can reuse it without a circular
# import - see that module's docstring. Only the two things below are the
# pane's own: the icon-scale baseline, and applying a size to every pane.

# The pane font size before this session zoomed anything, which is what the
# icons are scaled relative to. It can only be read off a live view that has
# not been given an override stylesheet yet, so it is captured once, at the
# first moment either code path has a pane in hand - see docs/ICONS.md.
_base_pane_font_size = None

def _pane_font(pane):
	# The theme's actual pane font (respects a user Theme.css), read off the
	# live view. Passed to core/font_size as a callable, not a QFont: reaching
	# through a pane that is going away raises, and that has to be caught
	# where the fallback is.
	return pane._widget._file_view.font()

@run_in_main_thread
def _apply_pane_font_size(pane, size):
	# size=None removes our override stylesheet so the pane falls back to
	# whatever the app-wide theme (Theme.css) sets.
	css = '' if size is None else 'FileListView { font-size: %dpt; }' % size
	pane._widget._file_view.setStyleSheet(css)

def _remember_base_pane_font_size(pane):
	# Call before applying an override to `pane`: afterwards the view reports
	# the override, and the theme's own size is gone for the session.
	global _base_pane_font_size
	if _base_pane_font_size is None:
		_base_pane_font_size = effective_font_size(lambda: _pane_font(pane))

def _apply_zoom_scale(size):
	# The icons and the command palette zoom with the pane text, from
	# whatever size the theme or the user picked for them: the engine
	# multiplies its own resolved icon size (and the palette's own font
	# sizes) by this, so "Set icon size 48" zooms from 48 rather than from
	# Qt's 16. One factor for both, computed once - they can only disagree
	# if something derives it twice.
	if size is None or not _base_pane_font_size:
		factor = 1.0
	else:
		factor = size / _base_pane_font_size
	set_icon_scale(factor)
	set_palette_font_scale(factor)

def _apply_to_all_panes(window, size):
	for pane in window.get_panes():
		_apply_pane_font_size(pane, size)
	_apply_zoom_scale(size)

def _change_pane_font_size(window, delta):
	first_pane = window.get_panes()[0]
	# Before the step, not after: once an override is applied the view reports
	# it, and the theme's own size - the icon scale's baseline - is gone.
	_remember_base_pane_font_size(first_pane)
	change_font_size(
		_SETTING_KEY, lambda: _pane_font(first_pane),
		lambda size: _apply_to_all_panes(window, size), delta
	)

def _reset_pane_font_size(window):
	reset_font_size(
		_SETTING_KEY, lambda size: _apply_to_all_panes(window, size)
	)

class IncreasePaneFontSize(DirectoryPaneCommand):

	aliases = ('Increase font size',)

	def __call__(self):
		_change_pane_font_size(self.pane.window, +1)

class DecreasePaneFontSize(DirectoryPaneCommand):

	aliases = ('Decrease font size',)

	def __call__(self):
		_change_pane_font_size(self.pane.window, -1)

class ResetPaneFontSize(DirectoryPaneCommand):

	# Palette-only by design — no default key binding requested.
	aliases = ('Reset font size',)

	def __call__(self):
		_reset_pane_font_size(self.pane.window)

class InitPaneFontSize(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# Mirrors InitHiddenFilesFilter: fman instantiates commands lazily,
		# so re-applying a saved setting on startup has to happen here.
		size = get_saved_font_size(_SETTING_KEY)
		# Unconditionally, and before applying: this is the only moment in a
		# session where the pane still reports the theme's own font size, so
		# it is the only moment the icon scale's baseline can be read.
		_remember_base_pane_font_size(self.pane)
		if size is not None:
			_apply_pane_font_size(self.pane, size)
			_apply_zoom_scale(size)
