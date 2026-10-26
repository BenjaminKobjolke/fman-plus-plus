"""The file view's columns: which ones are shown, and which one sorts.

Visibility is a Core setting applied straight to the live Qt view, because
fman has no pane.set_columns(...) - see `_apply_column_visibility`. The sort
column is remembered per directory in 'Sort Settings.json' and restored by
`RememberSortSettings` before each location change.
"""
from core.quicksearch_matchers import contains_chars, \
	contains_chars_after_separator, matched_in_order
from core.settings import get_setting, save_setting
from fman import DirectoryPaneCommand, DirectoryPaneListener, load_json, \
	QuicksearchItem, save_json, show_quicksearch
from fman.fs import resolve
from fman.impl.util.qt.thread import run_in_main_thread

__all__ = [
	'InitColumnVisibility', 'RememberSortSettings', 'SortByColumn',
	'ToggleModifiedColumn', 'ToggleSizeColumn'
]

# fman has no pane.set_columns(...) - the FileSystem owns the column set and
# the model is rebuilt on every navigation. So we hide/show columns directly
# on the live Qt view instead, keyed by the columns' qualified names.
_COLUMN_SETTING_KEYS = {
	'core.Size': 'hide_size_column',
	'core.Modified': 'hide_modified_column',
}

def _get_hidden_flags(columns):
	# Every index gets a flag: Qt keeps a section hidden across navigation, so a
	# column a filesystem doesn't share with file:// (eg. DriveSize) must be unhidden.
	return [
		col in _COLUMN_SETTING_KEYS and _is_column_hidden(col) for col in columns
	]

def _is_column_hidden(col_qual_name):
	key = _COLUMN_SETTING_KEYS[col_qual_name]
	return get_setting('Core Settings.json', key, False)

def _set_column_hidden(col_qual_name, hidden):
	save_setting('Core Settings.json', _COLUMN_SETTING_KEYS[col_qual_name], hidden)

@run_in_main_thread
def _apply_column_visibility(pane):
	columns = pane.get_columns()
	view = pane._widget._file_view
	# setColumnHidden(...) resizes the section (to 0 when hiding, back to its
	# old width when showing). Either resize fires sectionResized ->
	# ResizeColumnsToContents._on_col_resized, which then overwrites the
	# width we just set with its own idea of the "right" width - undoing the
	# show/hide until the next navigation resets that handler's state.
	# _handle_col_resize is the same reentrancy guard _on_col_resized itself
	# uses; toggling it here (rather than view.horizontalHeader().blockSignals)
	# only suppresses that one handler, so the header's other signals still
	# fire and the view still repaints/relayouts normally.
	view._handle_col_resize = False
	try:
		for index, hidden in enumerate(_get_hidden_flags(columns)):
			view.setColumnHidden(index, hidden)
	finally:
		view._handle_col_resize = True
	# setColumnHidden(...) alone doesn't relayout the visible columns to fill
	# the freed/needed width - that normally only happens on the next
	# resizeEvent (e.g. the user resizing the window). Force it now so
	# toggling is visible immediately.
	view.fit_name_column = get_setting(
		'Core Settings.json', 'fit_name_column', True
	)
	view.resizeColumnsToContents()

def _toggle_column(window, col_qual_name):
	_set_column_hidden(col_qual_name, not _is_column_hidden(col_qual_name))
	for pane in window.get_panes():
		_apply_column_visibility(pane)

class ToggleSizeColumn(DirectoryPaneCommand):

	# Palette-only by design - no default key binding requested.
	aliases = ('Toggle size column',)

	def __call__(self):
		_toggle_column(self.pane.window, 'core.Size')

class ToggleModifiedColumn(DirectoryPaneCommand):

	# Palette-only by design - no default key binding requested.
	aliases = ('Toggle modified column',)

	def __call__(self):
		_toggle_column(self.pane.window, 'core.Modified')

class InitColumnVisibility(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# Mirrors InitPaneFontSize: re-apply the saved setting on startup.
		_apply_column_visibility(self.pane)
	def on_path_changed(self):
		# The model (and its columns) is rebuilt on every navigation, so the
		# hidden state has to be re-applied each time, not just on startup.
		_apply_column_visibility(self.pane)

class SortByColumn(DirectoryPaneCommand):

	_MATCHERS = (contains_chars_after_separator(' '), contains_chars)

	def __call__(self, column_index=None):
		columns = self.pane.get_columns()
		if column_index is None:
			curr_sort_col = self.pane.get_sort_column()[0]
			curr_sort_col_index = columns.index(curr_sort_col)
			result = show_quicksearch(
				lambda q: self._get_items(columns, q), item=curr_sort_col_index
			)
			if result:
				column_index = columns.index(result[1])
		if column_index is not None:
			column = columns[column_index]
			sort_column, sort_column_is_ascending = self.pane.get_sort_column()
			if column == sort_column:
				ascending = not sort_column_is_ascending
			else:
				ascending = True
			self.pane.set_sort_column(column, ascending)
	def _get_items(self, columns, query):
		return matched_in_order(
			self._MATCHERS,
			[(name.rsplit('.', 1)[1], name) for name in columns], query,
			QuicksearchItem
		)

class RememberSortSettings(DirectoryPaneListener):
	def before_location_change(self, url, sort_column='', ascending=True):
		self._remember_curr_sort_column()
		try:
			# Consider: We're at zip:///foo.zip and go up. This moves us to
			# zip:/// - which resolves to file:///. The sort settings will have
			# been saved for this latter URL. So we have to resolve(...) to go
			# from the former to the latter:
			url_resolved = resolve(url)
		except OSError:
			url_resolved = url
		settings = load_json('Sort Settings.json', default={})
		try:
			data = settings[url_resolved]
		except KeyError:
			return
		remembered_col, remembered_asc = data['column'], data['is_ascending']
		# Note that we return `url` here, not `url_resolved`. This is eg.
		# because we don't want to rewrite C:\Windows\System32 -> ...\SysWOW64.
		return url, remembered_col, remembered_asc
	def _remember_curr_sort_column(self):
		column, is_ascending = self.pane.get_sort_column()
		url = self.pane.get_path()
		settings = load_json('Sort Settings.json', default={})
		default = (self.pane.get_columns()[0], True)
		if (column, is_ascending) == default:
			settings.pop(url, None)
		else:
			settings[url] = {
				'column': column,
				'is_ascending': is_ascending
			}
		save_json('Sort Settings.json')
