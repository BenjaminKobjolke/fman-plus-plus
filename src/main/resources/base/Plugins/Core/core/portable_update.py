"""Extract and launch updates for a portable Windows installation."""
import os
import shutil
import subprocess
import tempfile
import zipfile


PORTABLE_ASSET = 'fmanPortable.zip'


def extract_update(zip_path, dest_dir):
	with zipfile.ZipFile(zip_path) as archive:
		names = archive.namelist()
		if 'fman++/fman.exe' not in names:
			raise ValueError('Portable update archive has no fman++/fman.exe')
		for name in names:
			normalized_name = name.replace('\\', '/')
			path = normalized_name.split('/')
			if (normalized_name.startswith('/') or ':' in path[0]
					or any(part == '..' for part in path)):
				raise ValueError('Portable update archive contains an unsafe path')

		if os.path.exists(dest_dir):
			shutil.rmtree(dest_dir)
		os.makedirs(dest_dir)
		archive.extractall(dest_dir)

	return os.path.join(dest_dir, 'fman++')


def start_swap(source_dir, app_dir):
	helper = os.path.join(
		os.path.dirname(__file__), '..', 'bin', 'windows', 'portable_update.ps1'
	)
	copy_path = os.path.join(tempfile.gettempdir(), 'portable_update.ps1')
	shutil.copyfile(helper, copy_path)

	command = [
		'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
		'-WindowStyle', 'Hidden', '-File', copy_path,
		'-ProcessId', str(os.getpid()),
		'-Source', source_dir,
		'-Target', app_dir,
		'-RestartPath', os.path.join(app_dir, 'fman.exe'),
	]
	creationflags = (
		getattr(subprocess, 'DETACHED_PROCESS', 0)
		| getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
	)
	subprocess.Popen(
		command,
		creationflags=creationflags,
		stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
	)
