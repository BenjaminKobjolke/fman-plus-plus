"""Describe the checkout and interpreter used by the UI automation driver."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class BuildInfo:
	version: str | None
	commit: str | None
	dirty: bool | None
	checkout_path: str
	python: str

	def to_dict(self) -> dict[str, object]:
		return asdict(self)


def _git_output(repo_root: Path, *args: str) -> str | None:
	try:
		result = subprocess.run(
			['git', *args], cwd=repo_root, check=False,
			capture_output=True, text=True)
	except OSError:
		return None
	if result.returncode != 0:
		return None
	return result.stdout.strip()


def describe_build(repo_root: Path, python: str) -> BuildInfo:
	repo_root = Path(repo_root).resolve()
	version_path = repo_root / 'src' / 'build' / 'settings' / 'base.json'
	try:
		settings = json.loads(version_path.read_text(encoding='utf-8'))
		version = settings.get('version') if isinstance(settings, dict) else None
	except (OSError, ValueError):
		version = None
	if not isinstance(version, str):
		version = None

	commit = _git_output(repo_root, 'rev-parse', '--short', 'HEAD')
	status = _git_output(repo_root, 'status', '--porcelain')
	return BuildInfo(
		version=version,
		commit=commit or None,
		dirty=None if status is None else bool(status),
		checkout_path=str(repo_root),
		python=python,
	)
