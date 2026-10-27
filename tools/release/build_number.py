"""Bump and print fman's semantic version for the release workflow.

The version lives in ``src/build/settings/base.json``. Each release increments
its patch number, rolling over to the next minor version after patch 10.
The newest plain release tag is a floor when a settings version bump is lost.

Usage: ``python build_number.py [get|increment|decrement|label]``
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PATCH_MAX = 10
_FALLBACK_VERSION = "0.0.0"
# tools/release/build_number.py -> project root is two parents up.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS_FILE = _PROJECT_ROOT / "src" / "build" / "settings" / "base.json"
_VERSION_PATTERN = re.compile(r'("version"\s*:\s*")[^"]*(")')
_RELEASE_TAG_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def next_version(version: str) -> str:
    """Return the next version, rolling over after ``PATCH_MAX``."""
    segments = version.split(".")
    if len(segments) < 2 or any(not segment.isdecimal() for segment in segments):
        raise ValueError(f"invalid semantic version: {version!r}")

    numbers = [int(segment) for segment in segments]
    if numbers[-1] + 1 > PATCH_MAX:
        numbers[-2] += 1
        numbers[-1] = 0
    else:
        numbers[-1] += 1
    return ".".join(str(number) for number in numbers)


def _settings_version() -> str:
    if not _SETTINGS_FILE.exists():
        return _FALLBACK_VERSION
    data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    return str(data.get("version", _FALLBACK_VERSION))


def _git_tags() -> list[str]:
    # Some callers (including the release workflow's isolated checks) copy this
    # script into a temporary directory without the repository metadata.
    if not (_PROJECT_ROOT / ".git").exists():
        return []
    return subprocess.check_output(
        ["git", "tag", "--list"],
        cwd=_PROJECT_ROOT,
        text=True,
    ).split()


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(segment) for segment in value.split("."))


def released_version() -> str | None:
    # Releases are tagged in this checkout; fetch tags if releases move elsewhere.
    versions = [tag for tag in _git_tags() if _RELEASE_TAG_PATTERN.fullmatch(tag)]
    return max(versions, key=_version_key) if versions else None


def version() -> str:
    settings_version = _settings_version()
    tag_version = released_version()
    # A lost settings bump must not make the release reuse a shipped tag.
    if (
        tag_version is not None
        and _version_key(tag_version) > _version_key(settings_version)
    ):
        return tag_version
    return settings_version


def _write_version(value: str) -> None:
    contents = _SETTINGS_FILE.read_text(encoding="utf-8")
    updated, count = _VERSION_PATTERN.subn(rf'\g<1>{value}\g<2>', contents, count=1)
    if count != 1:
        raise ValueError(f"could not find version string in {_SETTINGS_FILE}")
    _SETTINGS_FILE.write_text(updated, encoding="utf-8")


def increment() -> str:
    value = next_version(version())
    _write_version(value)
    return value


def decrement() -> str:
    contents = subprocess.check_output(
        ["git", "show", "HEAD:src/build/settings/base.json"],
        cwd=_PROJECT_ROOT,
        text=True,
    )
    value = str(json.loads(contents).get("version", _FALLBACK_VERSION))
    _write_version(value)
    return value


def label() -> str:
    return version()


_COMMANDS = {
    "get": label,
    "increment": increment,
    "decrement": decrement,
    "label": label,
}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    action = args[0] if args else "get"
    handler = _COMMANDS.get(action)
    if handler is None:
        print(f"usage: python build_number.py [{'|'.join(_COMMANDS)}]")
        return 2
    print(handler())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
