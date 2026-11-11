"""Run the loopback FTP server used only by the demo recording fixture."""

import logging
import shutil
import sys
import time
from pathlib import Path

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import ThreadedFTPServer

PORT = 21217
LISTING_DELAY_S = 2.0
UPLOAD_DELAY_S = 1.0
LIFETIME_S = 180


def _seed(root: Path) -> None:
	if (
		root.name != "fman-demo-17-ftp"
	):
		raise ValueError("Refusing to seed an unexpected FTP fixture directory")
	if root.exists():
		shutil.rmtree(root)
	(root / "site" / "css").mkdir(parents=True)
	(root / "site" / "css" / "style.css").write_text(
		"body { color: black; }\n", encoding="utf-8",
	)


def _handler_type() -> type[FTPHandler]:
	class DelayedFTPHandler(FTPHandler):
		def _delay_listing(self) -> None:
			time.sleep(LISTING_DELAY_S)

		def ftp_LIST(self, path: str) -> None:
			self._delay_listing()
			super().ftp_LIST(path)

		def ftp_MLSD(self, path: str) -> None:
			self._delay_listing()
			super().ftp_MLSD(path)

		def ftp_NLST(self, path: str) -> None:
			self._delay_listing()
			super().ftp_NLST(path)

		def ftp_MLST(self, path: str) -> None:
			self._delay_listing()
			super().ftp_MLST(path)

		def ftp_STAT(self, path: str) -> None:
			self._delay_listing()
			super().ftp_STAT(path)

		def ftp_SIZE(self, path: str) -> None:
			self._delay_listing()
			super().ftp_SIZE(path)

		def ftp_MDTM(self, path: str) -> None:
			self._delay_listing()
			super().ftp_MDTM(path)

		def ftp_STOR(self, file: str, mode: str = "w") -> None:
			# A slow server keeps the progress window up when the question opens.
			time.sleep(UPLOAD_DELAY_S)
			super().ftp_STOR(file, mode)

	return DelayedFTPHandler


def main(root: Path) -> None:
	_seed(root)
	logging.getLogger("pyftpdlib").setLevel(logging.CRITICAL)
	authorizer = DummyAuthorizer()
	authorizer.add_user("demo", "demo", str(root), perm="elradfmwMT")
	handler = _handler_type()
	handler.authorizer = authorizer
	server = ThreadedFTPServer(("127.0.0.1", PORT), handler)
	started_at = time.monotonic()
	try:
		while time.monotonic() - started_at < LIFETIME_S:
			server.serve_forever(timeout=0.5, blocking=False)
	finally:
		server.close_all()


if __name__ == "__main__":
	if len(sys.argv) != 2:
		raise SystemExit("Usage: demo_ftp_server.py <root>")
	main(Path(sys.argv[1]))
