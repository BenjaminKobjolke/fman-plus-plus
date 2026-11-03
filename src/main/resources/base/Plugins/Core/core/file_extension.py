"""Helpers for displaying and preserving a file's extension."""
from core.column_visibility import shows_name_without_extension
from os.path import splitext

def split_extension(name):
	stem, extension = splitext(name)
	if not extension or extension == '.':
		return name, ''
	return stem, extension[1:]

def name_for_name_column(fs, url):
	name = fs.query(url, 'name')
	if not shows_name_without_extension():
		return name
	try:
		if fs.is_dir(url):
			return name
	except OSError:
		return name
	# shortcut: also strips on plugin filesystems that use core.Name without an
	# Extension column; check the pane's columns if one needs it
	return split_extension(name)[0]

def name_with_hidden_extension(fs, url, edited_name):
	full = fs.query(url, 'name')
	shown = name_for_name_column(fs, url)
	if shown != full:
		return edited_name + full[len(shown):]
	return edited_name
