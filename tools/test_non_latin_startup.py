"""Guards against upstream #523: Qt losing its plugin path under non-Latin paths."""

import os
from importlib import import_module
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import psutil

ROOT = Path(__file__).resolve().parents[1]
FROZEN_DIR = ROOT / "target" / "fman"
NON_LATIN_NAME = "fman523_Пользователь_用户"
STARTUP_WAIT_SECONDS = 12
PROFILE_VARIABLES = ("USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")

sys.path.insert(0, str(ROOT / "tools" / "fman_ui"))
detached_popen = import_module("process_launch").detached_popen
kill_process = import_module("session_reaper").kill_process


@unittest.skipUnless(os.name == "nt", "requires a Windows frozen build")
class NonLatinStartupTest(unittest.TestCase):
    def setUp(self):
        if not (FROZEN_DIR / "fman.exe").is_file():
            self.skipTest(
                "No frozen build; create one with tools\\build_windows.bat "
                "or python build.py freeze."
            )

    def test_frozen_app_starts_with_non_latin_profile_paths(self):
        with tempfile.TemporaryDirectory(
            prefix=NON_LATIN_NAME + "_", ignore_cleanup_errors=True
        ) as temporary:
            root = Path(temporary)
            app = root / "app"
            shutil.copytree(
                FROZEN_DIR,
                app,
                ignore=shutil.ignore_patterns("portable.txt", "Data"),
            )

            profile = root / "Пользователь"
            roaming = profile / "AppData" / "Roaming"
            local = profile / "AppData" / "Local"
            temp = profile / "Temp"
            for folder in (roaming, local, temp):
                folder.mkdir(parents=True, exist_ok=True)

            env = os.environ.copy()
            env.pop("FMAN_DATA_DIRECTORY", None)
            env.update(
                {
                    "USERPROFILE": str(profile),
                    "APPDATA": str(roaming),
                    "LOCALAPPDATA": str(local),
                    "TEMP": str(temp),
                    "TMP": str(temp),
                }
            )

            process = detached_popen(
                [str(app / "fman.exe")],
                cwd=str(app),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            start_time = psutil.Process(process.pid).create_time()
            try:
                time.sleep(STARTUP_WAIT_SECONDS)
                self.assertIsNone(
                    process.poll(),
                    f"fman exited during startup with code {process.returncode}",
                )
                self.assertTrue(
                    (roaming / "fman").exists(),
                    "fman did not create its settings folder under non-Latin APPDATA",
                )
            finally:
                kill_process(process.pid, start_time)
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
