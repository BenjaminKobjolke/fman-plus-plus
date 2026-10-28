from build_impl import copy_python_library, copy_release_notes
from fbs import path, SETTINGS
from fbs.cmdline import command
from fbs.freeze import windows as fbs_windows
from shutil import rmtree
from subprocess import run
from build_impl.version_info import brand_version_info
from zipfile import ZIP_DEFLATED, ZipFile


_create_version_info = fbs_windows._create_version_info


def _create_version_info_with_display_name():
	_create_version_info()
	version_info_path = path('target/PyInstaller/version_info.py')
	with open(version_info_path, 'r', encoding='utf-8') as version_info_file:
		source = version_info_file.read()
	with open(version_info_path, 'w', encoding='utf-8') as version_info_file:
		version_info_file.write(brand_version_info(
			source, SETTINGS['app_name'], SETTINGS['display_name']
		))
	# fbs passes this to PyInstaller as --version-file.
	return version_info_path


# fbs checks its bundled version_info.py before the project override, so the
# project file is never read. This relies on a private fbs function; remove the
# wrapper once fbs changes that lookup order.
fbs_windows._create_version_info = _create_version_info_with_display_name

@command
def freeze():
	fbs_windows.freeze_windows()
	copy_release_notes(path('${freeze_dir}/release_notes'))
	rmtree(path('${core_plugin_in_freeze_dir}/bin/mac'))
	rmtree(path('${core_plugin_in_freeze_dir}/bin/linux'))
	# Open Sans is only used on Linux. Further, it fails to load on some users'
	# Windows systems (see fman issue #480). Remove it to avoid problems,
	# improve startup performance and decrease fman's download size.
	# (Also note that a more elegant solution would be to only place
	# Open Sans in src/main/resources/*linux*/Plugins/Core. But the current
	# implementation cannot handle multiple dirs .../resources/main,
	# .../resources/linux for one plugin.)
	# The whole directory, so its LICENSE goes with the font it covers - a
	# licence left behind for a font that is not shipped is just confusing.
	rmtree(path('${core_plugin_in_freeze_dir}/Fonts/Open Sans'))
	copy_python_library('send2trash', path('${core_plugin_in_freeze_dir}'))
	# core.release_notes (Core plugin) imports this to detect the system
	# language for locale fallback - not scanned by PyInstaller since plugin
	# code is bundled as data, so it's copied in explicitly like send2trash:
	copy_python_library('python_localization', path('${core_plugin_in_freeze_dir}'))

@command
def sign():
	# fbs's own sign() uses a local signtool + certificate.pfx that expired
	# 2022-07-03. Use the XIDA network-share signing handshake instead
	# (tools/sign_exe.bat -> release-tool's PreSigner).
	_sign_exe(path('${freeze_dir}/fman.exe'))

@command
def sign_installer():
	_sign_exe(path('target/fmanSetup.exe'))

def _sign_exe(exe_path):
	run([path('tools/sign_exe.bat'), exe_path], shell=True, check=True)

@command
def portable_zip():
	# Keep the asset name in sync with core/portable_update.py, release_create.ini,
	# github_release.bat and build_release.bat.
	write_portable_zip(
		path('${freeze_dir}'), path('src/build/portable/portable.txt'),
		path('target/fmanPortable.zip')
	)

def write_portable_zip(freeze_dir, marker_path, zip_path):
	with ZipFile(zip_path, 'w', ZIP_DEFLATED) as archive:
		for source_path in freeze_dir.rglob('*'):
			relative_path = source_path.relative_to(freeze_dir)
			if relative_path.parts[0] == 'Data' or relative_path.name == 'portable.txt':
				continue
			if source_path.is_file():
				archive.write(source_path, 'fman++/' + relative_path.as_posix())
		archive.write(marker_path, 'fman++/portable.txt')

@command
def upload():
	# This fork does not have access to the original project's AWS account, and
	# doesn't publish to update.fman.io (that's Michael Herrmann's distribution
	# channel, not ours). Distribution instead goes through GitHub Releases —
	# see docs/CREATE_NEW_RELEASE.md step 4.5 / tools/github_release.bat.
	pass
