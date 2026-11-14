from os.path import dirname, join
import sys
sys.path.append(join(dirname(__file__), *'src/build/python'.split('/')))
sys.path.append(join(dirname(__file__), 'tools'))

from fbs import path, activate_profile
from fbs.builtin_commands import clean
from fbs.cmdline import command
from fbs_pro import FBS_URL
from fbs_runtime.platform import is_windows, is_mac, is_linux, is_ubuntu, \
	is_fedora, is_arch_linux, linux_distribution
from os import makedirs
from os.path import dirname
from subprocess import run, PIPE

import fbs.cmdline

if is_windows():
	from build_impl.windows import freeze, upload, sign, sign_installer, portable_zip
	from fbs.builtin_commands import installer
elif is_mac():
	from build_impl.mac import freeze, sign, sign_installer, upload
	from fbs.builtin_commands import installer
elif is_linux():
	from fbs.builtin_commands import installer
	if is_ubuntu() or linux_distribution() == 'Debian GNU/Linux':
		from build_impl.ubuntu import freeze, upload
	elif is_arch_linux():
		from build_impl.arch import freeze, upload
		from fbs.builtin_commands import sign_installer
	elif is_fedora():
		from build_impl.fedora import freeze, upload
		from fbs.builtin_commands import sign_installer
	else:
		raise NotImplementedError(linux_distribution())

@command
def publish():
	if is_windows():
		freeze()
		sign()
		installer()
		sign_installer()
		portable_zip()
		upload()
	elif is_mac():
		freeze()
		sign()
		installer()
		sign_installer()
		upload()
	elif is_linux():
		if is_ubuntu():
			freeze()
			installer()
			upload()
		elif is_arch_linux():
			freeze()
			installer()
			sign_installer()
			upload()
		elif is_fedora():
			freeze()
			installer()
			sign_installer()
			upload()
		else:
			raise NotImplementedError()
	else:
		raise ValueError('Unknown operating system.')

@command
def release_build():
	# tools/release_create.bat (release-tool create) bumps the version in
	# base.json and authors release notes before building, then commits, tags
	# and pushes afterwards. This command builds that intentionally dirty tree.
	clean()
	activate_profile('release')
	publish()

@command
def requirements():
	"""
	Write requirements/*.txt from uv.lock for the Linux Docker images
	(fbs buildvm needs base.txt; the Dockerfiles pip-install <distro>.txt).
	"""
	exported = run(
		['uv', 'export', '--frozen', '--no-hashes', '--no-emit-project',
		 '--no-emit-package', 'fbs'],
		check=True, stdout=PIPE, text=True, cwd=path('.')
	).stdout
	makedirs(path('requirements'), exist_ok=True)
	_write_requirements('base.txt', 'fbs[sentry] @ %s\n%s' % (FBS_URL, exported))
	for distro in ('ubuntu', 'arch', 'fedora'):
		_write_requirements(distro + '.txt', '-r base.txt\n')

def _write_requirements(name, contents):
	# newline='\n': the files are read inside Linux containers.
	with open(path('requirements/' + name), 'w', newline='\n') as f:
		f.write(contents)

if __name__ == '__main__':
	project_dir = dirname(__file__)
	fbs.cmdline.main(project_dir)
