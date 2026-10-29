from build_impl import copy_release_notes, copy_python_library
from fbs import path
from fbs.cmdline import command
from fbs.freeze.mac import freeze_mac
from os import remove
from os.path import basename, isdir, isfile, islink, join
from shutil import rmtree, move
from subprocess import run

@command
def freeze():
	freeze_mac()
	copy_release_notes(path('${freeze_dir}/Contents/Resources/release_notes'))
	rmtree(path('${core_plugin_in_freeze_dir}/bin/linux'))
	rmtree(path('${core_plugin_in_freeze_dir}/bin/windows'))
	# Open Sans is only used on Linux. Further, it fails to load on some users'
	# Windows systems (see fman issue #480). Remove it to avoid problems,
	# improve startup performance and decrease fman's download size.
	# (Also note that a more elegant solution would be to only place
	# Open Sans in src/main/resources/*linux*/Plugins/Core. But the current
	# implementation cannot handle multiple dirs .../resources/main,
	# .../resources/linux for one plugin.)
	# Whole directories, so each LICENSE goes with the font it covers - a
	# licence left behind for a font that is not shipped is just confusing.
	rmtree(path('${core_plugin_in_freeze_dir}/Fonts/Open Sans'))
	# Similarly for Roboto. It is only used on Windows:
	rmtree(path('${core_plugin_in_freeze_dir}/Fonts/Roboto'))
	_strip_unused_from_bundle()
	copy_python_library('osxtrash', path('${core_plugin_in_freeze_dir}'))
	# core.release_notes imports this to detect the system language; plugin
	# code is bundled as data, so PyInstaller doesn't collect it automatically.
	copy_python_library('python_localization', path('${core_plugin_in_freeze_dir}'))
	import osxtrash
	so_name = basename(osxtrash.__file__)
	# Move the .so to Frameworks (where PyInstaller 6.x sets sys._MEIPASS),
	# so it remains importable in the frozen app:
	move(
		path('${core_plugin_in_freeze_dir}/' + so_name),
		path('${freeze_dir}/Contents/Frameworks')
	)
	move(
		path('${core_plugin_in_freeze_dir}/bin/mac/7zz'),
		path('${freeze_dir}/Contents/MacOS')
	)

def _strip_unused_from_bundle():
	resources = path('${freeze_dir}/Contents/Resources')
	frameworks = path('${freeze_dir}/Contents/Frameworks')
	# Remove unused Qt frameworks (fman only uses Core, Gui, Widgets,
	# MacExtras, PrintSupport, Svg):
	qt_lib = join(frameworks, 'PyQt5', 'Qt5', 'lib')
	for unused_fw in (
		'QtQml', 'QtQmlModels', 'QtQuick', 'QtWebSockets'
	):
		fw_path = join(qt_lib, unused_fw + '.framework')
		if isdir(fw_path):
			rmtree(fw_path)
		# PyInstaller also places top-level symlinks pointing into the
		# framework. Remove them too; otherwise they dangle and Gatekeeper
		# rejects the bundle ("invalid destination for symbolic link"):
		for symlink_dir in (resources, frameworks):
			symlink = join(symlink_dir, unused_fw)
			if islink(symlink):
				remove(symlink)
	# Remove unused Qt platform plugins:
	qt_plugins = join(frameworks, 'PyQt5', 'Qt5', 'plugins')
	for unused_plugin in (
		'platforms/libqwebgl.dylib', 'platforms/libqminimal.dylib',
		'platforms/libqoffscreen.dylib', 'bearer', 'generic',
		'platformthemes'
	):
		p = join(qt_plugins, unused_plugin)
		if isdir(p):
			rmtree(p)
		elif isfile(p):
			remove(p)

@command
def sign():
	_sign_mac(
		path('${freeze_dir}'), '--entitlements',
		path('src/sign/mac/entitlements.plist')
	)

@command
def sign_installer():
	_sign_mac(path('target/fman.dmg'))

def _sign_mac(file_path, *args):
	# Signing, notarization and stapling live in release-tool's mac-sign.
	run([path('tools/sign_mac.sh'), file_path] + list(args), check=True)

@command
def upload():
	# This fork publishes through GitHub Releases, not update.fman.io.
	pass
