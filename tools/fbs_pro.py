"""
Download the fbs Pro sdist into vendor/, where pyproject.toml's fbs source
points. uv rejects FBS_URL itself: it has no archive extension, and uv does not
read the Content-Disposition filename the way pip does (build.py's
`requirements` command still hands the URL to pip for the Docker images).

Stdlib only: install.bat runs this before .venv exists. uv.lock pins the
archive's sha256, so `uv sync` rejects a download that changed.
"""

from pathlib import Path
from urllib.request import urlopen

FBS_VERSION = '1.2.7'
FBS_URL = 'https://build-system.fman.io/pro/' \
	'b5aab865-bd29-4f23-992c-0eb4f3a24f33/' + FBS_VERSION
# Saved as fbs-..., not the server's fbs_pro-..., so the sdist filename matches
# the package name.
FBS_ARCHIVE = Path(__file__).resolve().parents[1] / 'vendor' / \
	('fbs-%s.tar.gz' % FBS_VERSION)

def main():
	if FBS_ARCHIVE.exists():
		return
	print('Downloading fbs Pro %s...' % FBS_VERSION)
	partial = FBS_ARCHIVE.with_name(FBS_ARCHIVE.name + '.part')
	with urlopen(FBS_URL) as response:
		partial.write_bytes(response.read())
	# Rename last, so an interrupted download is retried rather than used.
	partial.replace(FBS_ARCHIVE)

if __name__ == '__main__':
	main()
