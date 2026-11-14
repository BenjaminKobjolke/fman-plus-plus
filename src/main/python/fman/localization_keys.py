"""Keys for text owned by fman and its built-in Core plugin."""

QUICKSEARCH_TITLE = 'quicksearch_title'
QUICKSEARCH_KEY_ENTER = 'quicksearch_key_enter'
QUICKSEARCH_RUN = 'quicksearch_run'
QUICKSEARCH_KEY_SHIFT_ENTER = 'quicksearch_key_shift_enter'
QUICKSEARCH_MORE_ACTIONS = 'quicksearch_more_actions'
COMMAND_PALETTE_TITLE = 'command_palette_title'
GOTO_TITLE = 'goto_title'
READY = 'status_ready'
ERROR_DISMISS = 'error_dismiss'
PROMPT_OK = 'prompt_ok'
PROMPT_CANCEL = 'prompt_cancel'
TEXT_INPUT_SAVE = 'text_input_save'
TEXT_INPUT_NEW_LINE = 'text_input_new_line'
ERROR_OPEN_CONSOLE = 'error_open_console'
ERROR_COPY = 'error_copy'
ERROR_COPIED = 'error_copied'
ERROR_REPORT_SEND = 'error_report_send'
ERROR_REPORT_SENT = 'error_report_sent'
ERROR_REPORTS_CONSENT = 'error_reports_consent'
ERROR_REPORTS_CONSENT_YES = 'error_reports_consent_yes'
ERROR_REPORTS_CONSENT_NO = 'error_reports_consent_no'
ERROR_REPORTS_ON = 'error_reports_on'
ERROR_REPORTS_OFF = 'error_reports_off'
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
GOTO_NETWORK_SEARCHING = 'goto_network_searching'
GOTO_NETWORK_NO_ANSWER = 'goto_network_no_answer'
GOTO_NETWORK_NO_SHARES = 'goto_network_no_shares'
COULD_NOT_READ = 'could_not_read'
COULD_NOT_CREATE = 'could_not_create'
SHORTCUT_TARGET_MISSING = 'shortcut_target_missing'
LINK_TARGET_PROMPT = 'link_target_prompt'
LINK_TARGET_MISSING_CONFIRM = 'link_target_missing_confirm'
LINK_TARGET_FAILED = 'link_target_failed'
FILE_COMMENT_TITLE = 'file_comment_title'
FILE_COMMENT_TITLE_MULTIPLE = 'file_comment_title_multiple'
FILE_COMMENT_LOCAL_ONLY = 'file_comment_local_only'
FILE_COMMENT_SAVE_FAILED = 'file_comment_save_failed'
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
	'Edit comment': 'command_edit_comment',
	'Toggle error reports': 'command_toggle_error_reports',
}

ENGLISH_TEXT = {
	QUICKSEARCH_TITLE: 'Quicksearch',
	QUICKSEARCH_KEY_ENTER: 'Enter',
	QUICKSEARCH_RUN: 'Run',
	QUICKSEARCH_KEY_SHIFT_ENTER: 'Shift+Enter',
	QUICKSEARCH_MORE_ACTIONS: 'More actions',
	COMMAND_PALETTE_TITLE: 'Command Palette',
	GOTO_TITLE: 'Go To',
	READY: 'Ready.',
	ERROR_DISMISS: 'Dismiss',
	PROMPT_OK: 'OK',
	PROMPT_CANCEL: 'Cancel',
	TEXT_INPUT_SAVE: 'Save',
	TEXT_INPUT_NEW_LINE: 'New line',
	ERROR_OPEN_CONSOLE: 'Open in console',
	ERROR_COPY: 'Copy error',
	ERROR_COPIED: 'Error copied to clipboard.',
	ERROR_REPORT_SEND: 'Send report',
	ERROR_REPORT_SENT: 'Error report sent.',
	ERROR_REPORTS_CONSENT: (
		'Would you like to send error reports? They help a lot to improve fman.'
	),
	ERROR_REPORTS_CONSENT_YES: 'Yes',
	ERROR_REPORTS_CONSENT_NO: 'No',
	ERROR_REPORTS_ON: 'Error reporting on.',
	ERROR_REPORTS_OFF: 'Error reporting off.',
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
	GOTO_NETWORK_SEARCHING: 'Searching network…',
	GOTO_NETWORK_NO_ANSWER: 'Did not answer',
	GOTO_NETWORK_NO_SHARES: 'No shared folders',
	COULD_NOT_READ: 'Could not read from %s (%s)',
	COULD_NOT_CREATE: 'Could not create %s (%s)',
	SHORTCUT_TARGET_MISSING: 'The destination of %s does not exist.',
	LINK_TARGET_PROMPT: 'New target for %s:',
	LINK_TARGET_MISSING_CONFIRM: '%s does not exist. Point the link there anyway?',
	LINK_TARGET_FAILED: 'Could not change the target of %s: %s',
	FILE_COMMENT_TITLE: 'Comment for %s',
	FILE_COMMENT_TITLE_MULTIPLE: 'Comment for %s files',
	FILE_COMMENT_LOCAL_ONLY: 'Comments can only be edited for local files.',
	FILE_COMMENT_SAVE_FAILED: 'Could not save file comment: %s',
	SAVE_CHANGES_BEFORE_CLOSING: 'Save changes before closing?',
}
ENGLISH_TEXT.update({key: title for title, key in COMMAND_TITLES.items()})

ALL_KEYS = tuple(ENGLISH_TEXT)
TEXT_KEYS = {text: key for key, text in ENGLISH_TEXT.items()}
TEXT_KEYS.update(COMMAND_TITLES)
