"""Keys for text owned by fman and its built-in Core plugin."""

QUICKSEARCH_TITLE = 'quicksearch_title'
READY = 'status_ready'
ERROR_DISMISS = 'error_dismiss'
ERROR_OPEN_CONSOLE = 'error_open_console'
ERROR_COPY = 'error_copy'
ERROR_COPIED = 'error_copied'
SYSTEM_LANGUAGE = 'language_system'
LANGUAGE_ENGLISH = 'language_english'
LANGUAGE_RUSSIAN = 'language_russian'
LANGUAGE_CURRENT = 'language_current'
LANGUAGE_RESTART = 'language_restart'
NO_FILE_FOR_EXTENSION = 'selection_no_file_for_extension'
NO_SELECTION = 'no_selection'
DELETE_CONFIRM = 'delete_confirm'
TRASH_CONFIRM = 'trash_confirm'
TRASH_LABEL_RECYCLE_BIN = 'trash_label_recycle_bin'
TRASH_LABEL_TRASH = 'trash_label_trash'
COULD_NOT_READ = 'could_not_read'
COULD_NOT_CREATE = 'could_not_create'
SHORTCUT_TARGET_MISSING = 'shortcut_target_missing'
SAVE_CHANGES_BEFORE_CLOSING = 'save_changes_before_closing'
COMMAND_TITLES = {
	'Help': 'command_help',
	'Do nothing': 'command_do_nothing',
	'Quit': 'command_quit',
	'Change language': 'command_change_language',
	'Show console': 'command_show_console',
	'Go up': 'command_go_up',
	'Reload': 'command_reload',
	'Delete': 'command_delete',
	'New folder': 'command_new_folder',
	'View file': 'command_view_file',
	'Go home': 'command_go_home',
	'Go to desktop': 'command_go_to_desktop',
	'Go to documents': 'command_go_to_documents',
	'Go to downloads': 'command_go_to_downloads',
	'Toggle hidden files': 'command_toggle_hidden_files',
	'Check for updates': 'command_check_for_updates',
	'Select theme': 'command_select_theme',
	'Select icon set': 'command_select_icon_set',
	'Open with...': 'command_open_with',
	'Copy': 'command_copy',
	'Paste': 'command_paste',
}

ENGLISH_TEXT = {
	QUICKSEARCH_TITLE: 'Quicksearch',
	READY: 'Ready.',
	ERROR_DISMISS: 'Dismiss',
	ERROR_OPEN_CONSOLE: 'Open in console',
	ERROR_COPY: 'Copy error',
	ERROR_COPIED: 'Error copied to clipboard.',
	SYSTEM_LANGUAGE: 'System language',
	LANGUAGE_ENGLISH: 'English',
	LANGUAGE_RUSSIAN: 'Russian',
	LANGUAGE_CURRENT: 'current',
	LANGUAGE_RESTART: 'Restart fman to apply the language change.',
	NO_FILE_FOR_EXTENSION: 'Put the cursor on a file to use its extension.',
	NO_SELECTION: 'No file is selected!',
	DELETE_CONFIRM: (
		'Do you really want to PERMANENTLY delete %s? '
		'This action cannot be undone!'
	),
	TRASH_CONFIRM: 'Do you really want to move %s to the %s?',
	TRASH_LABEL_RECYCLE_BIN: 'Recycle Bin',
	TRASH_LABEL_TRASH: 'Trash',
	COULD_NOT_READ: 'Could not read from %s (%s)',
	COULD_NOT_CREATE: 'Could not create %s (%s)',
	SHORTCUT_TARGET_MISSING: 'The destination of %s does not exist.',
	SAVE_CHANGES_BEFORE_CLOSING: 'Save changes before closing?',
}
ENGLISH_TEXT.update({key: title for title, key in COMMAND_TITLES.items()})

ALL_KEYS = tuple(ENGLISH_TEXT)
TEXT_KEYS = {text: key for key, text in ENGLISH_TEXT.items()}
TEXT_KEYS.update(COMMAND_TITLES)
