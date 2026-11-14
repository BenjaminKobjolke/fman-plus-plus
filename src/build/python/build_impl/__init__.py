from fbs import path
from fbs_runtime.platform import is_windows, is_mac, is_linux
from importlib import import_module
from os import remove
from os.path import dirname, join, isdir, basename
from shutil import copy, copytree
from subprocess import check_output

import sys
import re

def remove_if_exists(file_path):
	try:
		remove(file_path)
	except FileNotFoundError:
		pass

def copy_python_library(name, dest_dir):
	library = import_module(name)
	is_package = re.match(r'^__init__\.pyc?$', basename(library.__file__))
	if is_package:
		package_dir = dirname(library.__file__)
		copytree(package_dir, join(dest_dir, basename(package_dir)))
	else:
		copy(library.__file__, dest_dir)

def copy_release_notes(dest_dir):
	# release_notes/<version>_<build>/<locale>.json (docs/CREATE_NEW_RELEASE.md)
	# is authored at the project root, not under src/main/resources, so fbs
	# doesn't bundle it. The caller chooses the destination next to Plugins/
	# where core.release_notes.release_notes_dir() expects it. Skip the copy
	# when no release has been authored so an empty release_notes/ is harmless.
	src_dir = path('release_notes')
	if isdir(src_dir):
		copytree(src_dir, dest_dir)

def get_canonical_os_name():
	if is_windows():
		return 'windows'
	if is_mac():
		return 'mac'
	if is_linux():
		return 'linux'
	raise ValueError('Unknown operating system.')

def check_output_decode(*args, **kwargs):
	return check_output(*args, **kwargs).decode(sys.stdout.encoding)
