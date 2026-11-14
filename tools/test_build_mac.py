"""Exercise the Mac release handoff without Apple tools or a release-tool checkout."""

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_PYTHON = ROOT / "src" / "build" / "python"


def load_mac_module():
    sys.path.insert(0, str(BUILD_PYTHON))
    fbs = types.ModuleType("fbs")
    fbs.SETTINGS = {}
    fbs.path = lambda value: value
    fbs_cmdline = types.ModuleType("fbs.cmdline")
    fbs_cmdline.command = lambda function: function
    fbs_freeze = types.ModuleType("fbs.freeze")
    fbs_freeze.__path__ = []
    fbs_freeze_mac = types.ModuleType("fbs.freeze.mac")
    fbs_freeze_mac.freeze_mac = lambda: None
    fbs_runtime = types.ModuleType("fbs_runtime")
    fbs_runtime.__path__ = []
    fbs_platform = types.ModuleType("fbs_runtime.platform")
    fbs_platform.is_windows = lambda: False
    fbs_platform.is_mac = lambda: False
    fbs_platform.is_linux = lambda: False
    sys.modules.update({
        "fbs": fbs,
        "fbs.cmdline": fbs_cmdline,
        "fbs.freeze": fbs_freeze,
        "fbs.freeze.mac": fbs_freeze_mac,
        "fbs_runtime": fbs_runtime,
        "fbs_runtime.platform": fbs_platform,
    })
    import build_impl
    return importlib.import_module("build_impl.mac"), build_impl


def check_python_behavior():
    mac, build_impl = load_mac_module()
    calls = []
    mac.run = lambda args, **kwargs: calls.append((args, kwargs))
    mac.sign()
    assert calls == [([
        "tools/sign_mac.sh", "${freeze_dir}", "--entitlements",
        "src/sign/mac/entitlements.plist",
    ], {"check": True})], calls
    calls.clear()
    mac.sign_installer()
    assert calls == [(["tools/sign_mac.sh", "target/fman.dmg"], {"check": True})]
    assert not hasattr(mac, "_run_notarytool")
    assert not hasattr(mac, "_run_codesign")
    assert not hasattr(mac, "_zip_mac")
    source = (ROOT / "src/build/python/build_impl/mac.py").read_text()
    assert all(tool not in source for tool in ("codesign", "notarytool", "stapler"))
    calls.clear()
    mac.upload()
    assert calls == []

    with tempfile.TemporaryDirectory(prefix="fman-release-notes-") as temporary:
        base = Path(temporary)
        source_notes = base / "release_notes"
        source_notes.mkdir()
        (source_notes / "1.0.0").mkdir()
        (source_notes / "1.0.0" / "en.json").write_text("{}")
        build_impl.path = lambda value: (
            str(source_notes) if value == "release_notes" else value
        )
        destination = base / "bundle" / "release_notes"
        destination.parent.mkdir()
        build_impl.copy_release_notes(str(destination))
        assert (destination / "1.0.0" / "en.json").read_text() == "{}"
        shutil.rmtree(source_notes)
        build_impl.copy_release_notes(str(base / "not-created"))
        assert not (base / "not-created").exists()


def check_bash_scripts():
    bash = shutil.which("bash")
    if not bash:
        print("bash script checks skipped (bash is not on PATH)")
        return
    if os.name == "nt" and (
        "\\windows\\system32\\bash.exe" in bash.lower()
        or "\\windowsapps\\bash.exe" in bash.lower()
    ):
        print("bash script checks skipped (PATH bash is the WSL launcher)")
        return
    probe = subprocess.run([bash, "--version"], capture_output=True, text=True,
                           timeout=10)
    if probe.returncode != 0 or "GNU bash" not in probe.stdout:
        print("bash script checks skipped (PATH bash is not a local GNU Bash)")
        return

    with tempfile.TemporaryDirectory(prefix="fman-mac-scripts-") as temporary:
        root = Path(temporary) / "fman"
        tools = root / "tools"
        tools.mkdir(parents=True)
        release_tool = Path(temporary) / "release-tool"
        release_tool.mkdir()
        fake_bin = Path(temporary) / "bin"
        fake_bin.mkdir()
        for name in ("sign_mac.sh", "build_mac.sh"):
            shutil.copy2(ROOT / "tools" / name, tools / name)
        record_args = Path(temporary) / "uv-args"
        uv = fake_bin / "uv"
        uv.write_text(
            "#!/bin/bash\n"
            "printf '%s\\n' \"$@\" > \"$UV_ARGS\"\n"
            "exit \"${UV_EXIT:-0}\"\n"
        )
        uv.chmod(0o755)
        app = Path(temporary) / "fman.app"
        app.mkdir()

        def bash_path(path):
            cygpath = shutil.which("cygpath")
            if cygpath:
                return subprocess.run(
                    [cygpath, "-u", str(path)], capture_output=True, text=True,
                    check=True, timeout=10,
                ).stdout.strip()
            return str(path)

        env = dict(os.environ, RELEASE_TOOL_DIR=str(release_tool),
                   PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
                   UV_ARGS=str(record_args), UV_EXIT="7")
        result = subprocess.run([bash, str(tools / "sign_mac.sh"), str(app),
                                 "--entitlements", "x"], env=env,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 7, result.stdout + result.stderr
        assert record_args.read_text().splitlines() == [
            "run", "python", "-m", "release_tool", "mac-sign", bash_path(app),
            "--entitlements", "x",
        ], record_args.read_text()
        record_args.unlink()
        result = subprocess.run([bash, str(tools / "sign_mac.sh"),
                                 str(app / "missing")], env=env,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode != 0 and not record_args.exists()

        for name in ("build_mac.sh",):
            shutil.copy2(ROOT / "tools" / name, tools / name)
        release_scripts = tools / "release"
        release_scripts.mkdir()
        (release_scripts / "build_number.py").write_text("stub")
        (root / "build.py").write_text("stub")
        fake_python = fake_bin / "python3"
        fake_python.write_text(
            "#!/bin/bash\n"
            "if [[ $1 == tools/release/build_number.py ]]; "
            "then echo 1.0.0; exit 0; fi\n"
            "mkdir -p target; touch target/fman.dmg\n"
        )
        fake_python.chmod(0o755)
        git = shutil.which("git")
        if not git:
            print("build_mac.sh git checks skipped (git is not on PATH)")
            return
        def git_call(*args):
            return subprocess.run([git, "-C", str(root), *args], check=True,
                                  capture_output=True, text=True, timeout=30)
        git_call("init", "-q")
        git_call("config", "user.email", "test@example.invalid")
        git_call("config", "user.name", "Test")
        (root / "placeholder").write_text("test")
        git_call("add", "placeholder")
        git_call("commit", "-qm", "initial")
        env["FMAN_PYTHON"] = bash_path(fake_python)
        result = subprocess.run([bash, str(tools / "build_mac.sh")], env=env,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode != 0 and "checkout" in result.stderr.lower(), (
            result.stdout + result.stderr
        )
        git_call("tag", "1.0.0")
        result = subprocess.run([bash, str(tools / "build_mac.sh")], env=env,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        assert (root / "target/release_version.txt").read_text().strip() == "1.0.0"


if __name__ == "__main__":
    check_python_behavior()
    check_bash_scripts()
    print("Mac release checks OK")
