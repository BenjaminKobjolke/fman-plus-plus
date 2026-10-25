"""
Acting on the file an in-pane viewer is showing - the Delete file / Rename
file… palette entries every viewer gets through ViewerNavigator (see
core/viewer_navigation.py), plus the toggle deciding what happens after a
delete.

Both operations reuse the file list's own commands rather than reimplementing
them: core/commands/deletion.py's confirmation and delete task, and
core/commands/rename.py's name validation and rename task. What is new here is
only what the viewer context adds - deleting the file you are looking at has to
decide where to leave you afterwards.

Its own module rather than more of core/viewer_navigation.py, which is near
the project's 300-line file cap - same reason core/textviewer_save.py is
split off core/textviewer.py.
"""
from core.commands.deletion import confirm_delete, confirm_trash, delete, trash
from core.commands.editor import _find_extension_start
from core.commands.rename import rename_to
from core.settings import get_setting, save_setting, SETTINGS_FILE
from core.viewer_status import viewer_status
from fman import show_prompt
from fman.url import basename
from threading import Thread

_CLOSE_AFTER_DELETE_KEY = 'viewer_close_after_delete'

def _in_background(work):
	"""
	Runs `work()` off the Qt thread, the way fman runs every command
	(fman/impl/plugins/command_registry.py's _run_outside_main_thread).

	Not optional: submit_task runs its task on the calling thread, and the
	pane model's own notify_file_added/_removed are @transaction(
	synchronous=True), which asserts it is NOT on the main thread
	(fman/impl/model/model.py). A viewer palette action runs on the main
	thread, so deleting or renaming from there would change the file on disk
	and leave the file list showing it until a manual reload.
	"""
	Thread(target=work, daemon=True).start()

def get_close_after_delete():
	# Defaults to closing: stepping to the next file makes deleting the one
	# after it a single keypress, which is the point when culling a folder but
	# too easy to do by accident as a default.
	return bool(get_setting(SETTINGS_FILE, _CLOSE_AFTER_DELETE_KEY, True))

def toggle_close_after_delete(pane):
	new_value = not get_close_after_delete()
	save_setting(SETTINGS_FILE, _CLOSE_AFTER_DELETE_KEY, new_value)
	viewer_status(
		pane,
		'After deleting: %s' % ('close viewer' if new_value else 'next file')
	)
	return new_value

def after_delete_label():
	# Labels the action the entry performs, not the state it is in - the same
	# convention as ViewerNavigator.same_type_label().
	if get_close_after_delete():
		return 'Go to next file after deleting'
	return 'Close viewer after deleting'

def after_file_gone(pane, category, on_close):
	"""Show the cursor's next viewable file after a pane command moved this one."""
	# viewer_navigation imports this module for its palette rows.
	from core.viewer_navigation import accepts, advance, get_same_type_only
	cursor_file = pane.get_file_under_cursor()
	if get_close_after_delete() or not cursor_file:
		on_close()
	elif accepts(cursor_file, category, get_same_type_only(category)):
		pane.run_command('view_file')
		viewer_status(pane, basename(cursor_file))
	else:
		advance(pane, +1, category)
		if pane.get_file_under_cursor() == cursor_file:
			on_close()

def delete_current(pane, url, category, on_close):
	"""
	Deletes `url` using the file list command's confirmation, then either
	closes the viewer or advances it to the next file, per the toggle above.
	A plugin rewrite of `move_to_trash` to `delete_permanently`, as on FTP,
	selects permanent deletion and its confirmation.
	"""
	# Lazily imported: core/viewer_navigation.py imports this module for the
	# palette rows, so importing it back at module level would be circular -
	# the same reason _category defers core.viewers there.
	from core.viewer_navigation import advance
	command, args = pane._rewrite_command('move_to_trash', {'urls': [url]})
	urls = args['urls']
	if command == 'delete_permanently':
		confirm, submit = confirm_delete, delete
	else:
		confirm, submit = confirm_trash, trash
	if not confirm(urls):
		return
	if get_close_after_delete():
		on_close()
	else:
		advance(pane, +1, category)
		if pane.get_file_under_cursor() == url:
			# Nothing to advance to - advance() put the cursor back on the
			# file we are about to delete, so there is nothing left to show.
			on_close()
	# Last, on purpose: the cursor has to be off the file before the row it
	# sits on disappears.
	_in_background(lambda: submit(urls))

def rename_current(pane, url, on_renamed=None):
	"""
	Renames the file the viewer is showing. `on_renamed(new_url)` lets a
	viewer re-point itself; the image and video viewers pass none, having
	already loaded their content and navigating by the pane's cursor.
	"""
	old_name = basename(url)
	new_name, ok = show_prompt(
		'Rename to:', default=old_name,
		# Preselect the stem, like the Rename command does in the file list.
		selection_end=_find_extension_start(old_name)
	)
	if not ok:
		return
	def rename():
		# rename_to alerts and returns None for a name it rejects, so there is
		# nothing to report here in that case.
		new_url = rename_to(pane, url, new_name)
		if new_url is None:
			return
		if on_renamed is not None:
			on_renamed(new_url)
		viewer_status(pane, 'Renamed to %s' % basename(new_url))
	_in_background(rename)
