"""Column visibility is a Core setting applied to the live Qt view because
fman has no pane.set_columns(...).
"""
from core.settings import get_setting, save_setting

COLUMN_SETTINGS = {
	'core.Size': ('hide_size_column', False),
	'core.Modified': ('hide_modified_column', False),
	'core.file_columns.Extension': ('hide_extension_column', True),
	'core.file_columns.Version': ('hide_version_column', True),
	'core.file_columns.Attributes': ('hide_attributes_column', True),
}
NAME_WITHOUT_EXTENSION_KEY = 'name_without_extension'

def is_column_hidden(name):
	if name in COLUMN_SETTINGS:
		key, default = COLUMN_SETTINGS[name]
		return get_setting('Core Settings.json', key, default)
	return name in get_setting('Core Settings.json', 'hidden_columns', [])

def set_column_hidden(name, hidden):
	if name in COLUMN_SETTINGS:
		key, _ = COLUMN_SETTINGS[name]
		save_setting('Core Settings.json', key, hidden)
		return
	hidden_columns = get_setting('Core Settings.json', 'hidden_columns', [])
	if hidden and name not in hidden_columns:
		hidden_columns.append(name)
	elif not hidden:
		hidden_columns = [column for column in hidden_columns if column != name]
	save_setting('Core Settings.json', 'hidden_columns', hidden_columns)

def shows_name_without_extension():
	return get_setting(
		'Core Settings.json', NAME_WITHOUT_EXTENSION_KEY, False
	) and not is_column_hidden(
		'core.file_columns.Extension'
	)
