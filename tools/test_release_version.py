"""Check the release version handoff with fake build, close-fman and publisher tools.

Runs the real ``build_release.bat``, ``github_release.bat`` and
``release_create.bat`` in a temporary workspace: ``build.py`` is a stub and ``uv``
/ ``git`` are fakes on ``PATH``, so nothing is built, signed or uploaded.

Usage (from the project root): ``python tools/test_release_version.py``
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
RELEASE_TOOL = "D:\\GIT\\BenjaminKobjolke\\release-tool"
# The fake uploader always exits with this, so "reached the uploader and kept its
# exit code" (7) is distinguishable from "stopped before the upload" (1).
UPLOAD_EXIT = 7

FAKE_BUILD = """\
import shutil, sys
from pathlib import Path
root = Path(__file__).parent
if (root / "fail_build").exists():
    sys.exit(3)
shutil.rmtree(root / "target", ignore_errors=True)
(root / "target").mkdir()
if not (root / "no_installer").exists():
    (root / "target" / "fmanSetup.exe").write_text("installer")
"""


def run_batch(path, *args):
    return subprocess.run(
        ["cmd", "/d", "/c", "call", str(path), *args],
        capture_output=True, text=True, timeout=60,
    )


def copy_with_fake_tool(name, scripts, fake_tool):
    text = (TOOLS / name).read_text()
    assert RELEASE_TOOL in text, name + " no longer points at release-tool"
    (scripts / name).write_text(text.replace(RELEASE_TOOL, str(fake_tool)))


def check_release_version():
    with tempfile.TemporaryDirectory(prefix="release-version-") as temporary:
        root = Path(temporary)
        scripts = root / "tools"
        fake_tool = root / "release-tool"
        settings = root / "src" / "build" / "settings"
        notes = root / "release_notes" / "1.0.0"
        for directory in (scripts / "release", fake_tool, settings, notes):
            directory.mkdir(parents=True)
        (settings / "base.json").write_text('{"version": "1.0.0"}')
        (notes / "en.json").write_text("{}")
        (root / "build.py").write_text(FAKE_BUILD)
        (scripts / "close_running_fman.ps1").write_text(
            "param([string]$Directory)\n"
            "if (Test-Path (Join-Path $PSScriptRoot '..\\fman_running')) { exit 4 }\n"
            "exit 0\n"
        )
        (fake_tool / "uv.cmd").write_text(
            "@echo off\necho %*\nexit /b " + str(UPLOAD_EXIT) + "\n"
        )
        (fake_tool / "git.cmd").write_text(
            '@echo off\nif exist "%~dp0no_tag" exit /b 2\nexit /b 0\n'
        )
        shutil.copyfile(
            TOOLS / "release" / "build_number.py",
            scripts / "release" / "build_number.py",
        )
        shutil.copyfile(TOOLS / "build_release.bat", scripts / "build_release.bat")
        find_build_python = TOOLS / "find_build_python.bat"
        if find_build_python.exists():
            shutil.copyfile(find_build_python, scripts / find_build_python.name)
        copy_with_fake_tool("github_release.bat", scripts, fake_tool)
        copy_with_fake_tool("release_create.bat", scripts, fake_tool)
        build = scripts / "build_release.bat"
        publish = scripts / "github_release.bat"
        record = root / "target" / "release_version.txt"
        installer = root / "target" / "fmanSetup.exe"
        fake_site = root / "fake_site"
        (fake_site / "fbs").mkdir(parents=True)
        (fake_site / "fbs" / "__init__.py").write_text("")
        # find_build_python.bat uses <root>\.venv; point it at the real
        # interpreter (a junction needs no admin rights, unlike a symlink).
        (root / ".venv").mkdir()
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(root / ".venv" / "Scripts"),
             str(Path(sys._base_executable).parent)],
            check=True, stdout=subprocess.DEVNULL,
        )

        previous_path = os.environ.get("PATH", "")
        previous_pythonpath = os.environ.get("PYTHONPATH")
        previous_virtual_env = os.environ.get("VIRTUAL_ENV")
        os.environ["PATH"] = os.pathsep.join(
            [str(fake_tool), str(Path(sys.executable).parent), previous_path]
        )
        os.environ["PYTHONPATH"] = str(fake_site)
        try:
            result = run_batch(build)
            assert result.returncode == 0, result.stdout + result.stderr
            assert record.read_text().strip() == "1.0.0", (
                "Build must record its label"
            )

            (root / "fman_running").touch()
            sentinel = root / "target" / "untouched"
            sentinel.touch()
            result = run_batch(build)
            assert result.returncode == 4, (
                "A running fman must stop the release build: "
                + result.stdout + result.stderr
            )
            assert sentinel.exists(), "The build must not run while fman is open"
            assert not record.exists(), "A stopped build must invalidate its record"
            (root / "fman_running").unlink()

            # The watcher and uv venv can both precede the project .venv on PATH.
            watcher_venv = root / "watcher_venv" / "Scripts"
            uv_venv = root / "uv_venv" / "Scripts"
            for scripts_dir in (watcher_venv, uv_venv):
                scripts_dir.mkdir(parents=True)
                (scripts_dir / "python.cmd").write_text("@exit /b 9\n")
            os.environ["PATH"] = os.pathsep.join(
                [str(watcher_venv), str(uv_venv), str(fake_tool),
                 str(Path(sys.executable).parent), previous_path]
            )
            os.environ["VIRTUAL_ENV"] = str(uv_venv.parent)
            result = run_batch(build)
            assert result.returncode == 0, (
                "Build must use the project .venv, not stacked PATH venvs: "
                + result.stdout + result.stderr
            )
            assert record.read_text().strip() == "1.0.0"
            os.environ["PATH"] = os.pathsep.join(
                [str(fake_tool), str(Path(sys.executable).parent), previous_path]
            )
            if previous_virtual_env is None:
                os.environ.pop("VIRTUAL_ENV", None)
            else:
                os.environ["VIRTUAL_ENV"] = previous_virtual_env

            result = run_batch(publish)
            assert 'github-release "1.0.0"' in result.stdout, (
                result.stdout + result.stderr
            )
            assert "release_notes\\1.0.0\\en.json" in result.stdout, result.stdout
            assert result.returncode == UPLOAD_EXIT, (
                "Publisher must preserve upload failures"
            )
            (fake_tool / "no_tag").touch()
            result = run_batch(publish)
            assert result.returncode == 1, "An unpushed tag must stop publishing"
            (fake_tool / "no_tag").unlink()

            (notes / "en.json").unlink()
            result = run_batch(publish)
            assert result.returncode == 1, "Missing release notes must stop publishing"
            (notes / "en.json").write_text("{}")

            installer.unlink()
            result = run_batch(publish)
            assert result.returncode == 1, "A missing installer must stop publishing"
            installer.write_text("installer")

            # A build that fails keeps the old installer file around here, but
            # the real one overwrites it in place - so its record must be gone.
            (root / "fail_build").touch()
            result = run_batch(build)
            assert result.returncode == 3, "Build failures must propagate"
            assert not record.exists(), "A failed build must invalidate the old record"
            result = run_batch(publish)
            assert result.returncode == 1, "A missing build record must stop publishing"
            (root / "fail_build").unlink()

            # An installer from before the record existed is named explicitly.
            result = run_batch(publish, "1.0.0")
            assert 'github-release "1.0.0"' in result.stdout, (
                result.stdout + result.stderr
            )
            assert result.returncode == UPLOAD_EXIT, result.stdout + result.stderr

            (root / "no_installer").touch()
            result = run_batch(build)
            assert result.returncode == 1, "A build without an installer must fail"
            assert not record.exists(), "No installer, no record"

            result = run_batch(scripts / "release_create.bat", "--dry-run")
            assert result.returncode == UPLOAD_EXIT, (
                "Release launcher must preserve failures"
            )
        finally:
            os.environ["PATH"] = previous_path
            if previous_pythonpath is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = previous_pythonpath
            if previous_virtual_env is None:
                os.environ.pop("VIRTUAL_ENV", None)
            else:
                os.environ["VIRTUAL_ENV"] = previous_virtual_env


if __name__ == "__main__":
    check_release_version()
    print("release version handoff OK")
