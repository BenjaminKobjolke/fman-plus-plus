"""Create a loopback network share fixture for an isolated UI session."""

from dataclasses import dataclass
import ntpath
from pathlib import Path

from fixtures import make_fixture


SHARE_FOLDER = 'share'
LOOPBACK_HOST = 'localhost'


@dataclass(frozen=True)
class NetworkShareFixture:
	path: Path
	unc: str
	url: str


def loopback_unc(path: Path) -> str:
	path = str(path)
	drive, tail = ntpath.splitdrive(path)
	if len(drive) != 2 or drive[1] != ':':
		raise ValueError('Network share fixture path must be on a drive: %s' % path)
	return r'\\%s\%s$%s' % (LOOPBACK_HOST, drive[0], tail)


def network_url(unc: str) -> str:
	return 'network://' + unc.lstrip('\\').replace('\\', '/')


def make_network_share(session_root: Path, now: float) -> NetworkShareFixture:
	path = Path(session_root) / SHARE_FOLDER
	make_fixture(path, now)
	unc = loopback_unc(path)
	if not Path(unc).is_dir():
		raise RuntimeError(
			'Network share fixture %s is not reachable; loopback admin shares '
			'may be disabled.' % unc)
	return NetworkShareFixture(path, unc, network_url(unc))
