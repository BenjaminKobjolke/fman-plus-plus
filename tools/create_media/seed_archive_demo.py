"""Seed demo 30's fixture: an archive-named folder, a deep archive and numbered files.

deep.zip is written with writestr only, so it holds no folder entries: that is the
case 7-Zip's old */*/*/* exclusion hid, which #17109 fixed.
"""

import sys
import zipfile
from pathlib import Path

NUMBERED_FILES = ("file2", "file10", "file999999", "file1000000")
INNER_ENTRY = "inside-inner.txt"
DEEP_ENTRY = "level1/level2/level3/level4/deep-file.txt"


def seed(left: Path, right: Path) -> None:
	archive_named_folder = left / "old.zip"
	archive_named_folder.mkdir(parents=True, exist_ok=True)
	with zipfile.ZipFile(archive_named_folder / "inner.zip", "w") as inner:
		inner.writestr(INNER_ENTRY, "Opened from inside a folder named old.zip\n")
	right.mkdir(parents=True, exist_ok=True)
	with zipfile.ZipFile(right / "deep.zip", "w") as deep:
		deep.writestr(DEEP_ENTRY, "Four folders deep, no folder entries\n")
	for name in NUMBERED_FILES:
		(right / name).write_bytes(b'')


if __name__ == "__main__":
	if len(sys.argv) != 3:
		sys.exit("usage: seed_archive_demo.py <left-folder> <right-folder>")
	seed(Path(sys.argv[1]), Path(sys.argv[2]))
