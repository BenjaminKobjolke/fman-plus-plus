"""Check the portable Windows archive layout."""

import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "build" / "python"))

write_portable_zip = import_module("build_impl.windows").write_portable_zip


class PortableZipTest(unittest.TestCase):
    def test_archive_contains_app_and_marker_but_not_data(self):
        with tempfile.TemporaryDirectory(prefix="fman-portable-zip-") as temporary:
            root = Path(temporary)
            freeze_dir = root / "fman"
            freeze_dir.mkdir()
            (freeze_dir / "fman.exe").write_bytes(b"app")
            (freeze_dir / "runtime.dll").write_bytes(b"runtime")
            (freeze_dir / "Data").mkdir()
            (freeze_dir / "Data" / "settings.json").write_text("user data")
            (freeze_dir / "portable.txt").write_text("stray marker")
            marker = root / "portable.txt"
            marker.write_text("portable marker")
            archive_path = root / "fmanPortable.zip"

            write_portable_zip(freeze_dir, marker, archive_path)

            with ZipFile(archive_path) as archive:
                self.assertEqual(
                    archive.read("fman++/fman.exe"), b"app"
                )
                self.assertEqual(
                    archive.read("fman++/runtime.dll"), b"runtime"
                )
                self.assertEqual(
                    archive.read("fman++/portable.txt"), b"portable marker"
                )
                self.assertFalse(any(name.startswith("fman++/Data/")
                                     for name in archive.namelist()))
                self.assertFalse(any(name.endswith("settings.json")
                                     for name in archive.namelist()))


if __name__ == "__main__":
    unittest.main()
