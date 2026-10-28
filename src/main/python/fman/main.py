import atexit
import ctypes
import logging
import os
import sys

def main():
	# Registered first so this runs after every other exit handler.
	atexit.register(_skip_interpreter_teardown)
	from fman import APP_NAME, DATA_DIRECTORY
	from fman.impl.portable import check_writable, portable_data_directory
	if DATA_DIRECTORY == portable_data_directory():
		write_error = check_writable(DATA_DIRECTORY)
		if write_error is not None:
			message = (
				'The portable data folder cannot be written to:\n\n%s\n%s\n\n'
				'Move %s to a writable folder and try again.'
			) % (DATA_DIRECTORY, write_error, APP_NAME)
			ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
			_skip_interpreter_teardown.exit_code = 1
			sys.exit(1)
			return
	from fman.impl.application_context import get_application_context
	appctxt = get_application_context()
	exit_code = appctxt.run()
	_skip_interpreter_teardown.exit_code = exit_code
	sys.exit(exit_code)

def _skip_interpreter_teardown():
	# Destroying PyQt objects during interpreter teardown can crash in sip.
	try:
		logging.shutdown()
		for stream in (sys.stdout, sys.stderr):
			if stream is not None:
				try:
					stream.flush()
				except (OSError, ValueError):
					pass
	finally:
		# Must be reached whatever the above raises, or teardown runs after all.
		os._exit(_skip_interpreter_teardown.exit_code)
_skip_interpreter_teardown.exit_code = 1

def profile_main():
	# Import late to only incur the .0n sec time cost when necessary:
	import cProfile
	from fbs_runtime.application_context import is_frozen
	filename = 'fman.profile' if is_frozen() else None
	cProfile.run('main()', sort='cumtime', filename=filename)

if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == '--profile':
		sys.argv.pop(1)
		profile_main()
	else:
		main()
