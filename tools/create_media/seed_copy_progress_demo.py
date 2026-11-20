"""Seed demo 33's fixture with enough files to show the progress dialog.

The files hold real bytes, so the dialog's speed line shows a transfer rate
instead of the 0 Bytes/s an empty-file fixture gives.
"""

import sys
from pathlib import Path

FOLDER_NAME = "copy-progress"
FILE_COUNT = 4000
FILE_SIZE = 64 * 1024


def seed(left: Path) -> None:
	folder = left / FOLDER_NAME
	folder.mkdir(parents=True, exist_ok=True)
	payload = b"x" * FILE_SIZE
	for index in range(FILE_COUNT):
		(folder / f"file_{index:05d}.bin").write_bytes(payload)


if __name__ == "__main__":
	if len(sys.argv) != 2:
		sys.exit("usage: seed_copy_progress_demo.py <left-folder>")
	seed(Path(sys.argv[1]))
