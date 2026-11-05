"""Keep archive passwords in memory and prompt for them when needed."""

import os
from fman import Task, show_alert, show_prompt

_passwords = {}
WRONG_PASSWORD_MESSAGE = 'Wrong password.'

def get_password(archive_path):
	return _passwords.get(_key(archive_path))

def remember_password(archive_path, password):
	_passwords[_key(archive_path)] = password

def forget_password(archive_path):
	_passwords.pop(_key(archive_path), None)

def clear():
	_passwords.clear()

def is_password_error(output):
	output = output.lower()
	return any(marker in output for marker in (
		'enter password',
		'wrong password',
		'data error in encrypted file'
	))

def ask_password(archive_path, task, wrong_password=False):
	if wrong_password:
		try:
			task.show_alert(WRONG_PASSWORD_MESSAGE)
		except NotImplementedError:
			show_alert(WRONG_PASSWORD_MESSAGE)
	prompt = 'Password for %s:' % os.path.basename(archive_path)
	try:
		password, accepted = task.show_prompt(prompt, password=True)
	except NotImplementedError:
		# shortcut: Direct filesystem calls do not have a task dialog.
		password, accepted = show_prompt(prompt, password=True)
	if not accepted:
		raise Task.Canceled()
	return password

def _key(archive_path):
	return os.path.normcase(os.path.normpath(archive_path)).casefold()
