"""Create disposable fixture folders for the fman UI automation driver."""

import json
import os
from pathlib import Path
import shutil
import subprocess


AGE_FOLDER = 'ages'
LARGE_FOLDER = 'large'
MAX_LARGE_COUNT = 50000
DEEP_FOLDER = 'deep'
DEEP_LEVELS = 6
MAX_DEEP_SIBLINGS = 5000
DAY_SECONDS = 86400
CORE_SETTINGS_PATH = ('Plugins', 'User', 'Settings', 'Core Settings.json')
VIDEO_FIXTURE_NAME = 'video.mp4'
VIDEO_SOURCE = Path('examples/left_pane/dummy.mp4')
AGE_FIXTURE_DAYS = (
	('age_0d_fresh.txt', 0.1, False),
	('age_2d.txt', 2, False),
	('age_10d.txt', 10, False),
	('age_45d.txt', 45, False),
	('age_200d.txt', 200, False),
	('age_400d_old.txt', 400, False),
	('age_10d_hidden.txt', 10, True),
)


def _hide(path: Path) -> None:
	if os.name == 'nt':
		subprocess.run(['attrib', '+h', str(path)], check=True,
			stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_fixture(path: Path, now: float) -> None:
	path = Path(path)
	path.mkdir(parents=True, exist_ok=True)
	(path / 'visible.txt').write_text('visible fixture\n', encoding='utf-8')
	hidden = path / 'hidden.txt'
	hidden.write_text('hidden fixture\n', encoding='utf-8')
	(path / 'folder').mkdir(exist_ok=True)
	bracket_folder = path / '[--brackets--]'
	bracket_folder.mkdir(exist_ok=True)
	(bracket_folder / 'visible.txt').write_text(
		'visible fixture in a bracketed folder\n', encoding='utf-8')
	_hide(hidden)
	ages = path / AGE_FOLDER
	ages.mkdir(exist_ok=True)
	for name, days, is_hidden in AGE_FIXTURE_DAYS:
		age_file = ages / name
		age_file.write_text('age fixture\n', encoding='utf-8')
		mtime = now - days * DAY_SECONDS
		os.utime(age_file, (mtime, mtime))
		if is_hidden:
			_hide(age_file)


def copy_video_fixture(path: Path, repo_root: Path) -> None:
	source = Path(repo_root) / VIDEO_SOURCE
	if not source.is_file():
		raise FileNotFoundError('Video fixture source does not exist: %s' % source)
	shutil.copyfile(source, Path(path) / VIDEO_FIXTURE_NAME)


def validate_large_count(count: int) -> None:
	if count < 0 or count > MAX_LARGE_COUNT:
		raise ValueError(
			'--large must be between 0 and %d.' % MAX_LARGE_COUNT)


def make_large_folder(path: Path, count: int, now: float) -> None:
	validate_large_count(count)
	if count == 0:
		return
	large = Path(path) / LARGE_FOLDER
	large.mkdir(parents=True, exist_ok=True)
	for index in range(count):
		file_path = large / ('file_%05d.txt' % index)
		file_path.write_text('', encoding='utf-8')
		mtime = now - (index % 400) * DAY_SECONDS
		os.utime(file_path, (mtime, mtime))


def validate_deep_count(count: int) -> None:
	if count < 0 or count > MAX_DEEP_SIBLINGS:
		raise ValueError('--deep must be between 0 and 5000.')


def make_deep_folder(path: Path, count: int) -> Path | None:
	validate_deep_count(count)
	if count == 0:
		return None
	current = Path(path) / DEEP_FOLDER
	current.mkdir(parents=True, exist_ok=True)
	for level in range(1, DEEP_LEVELS + 1):
		for index in range(count):
			(current / ('sibling_%04d' % index)).mkdir(exist_ok=True)
		current = current / ('level_%d' % level)
		current.mkdir(exist_ok=True)
	return current


def parse_core_settings(text: str | None) -> dict[str, object] | None:
	if text is None:
		return None
	settings = json.loads(text)
	if not isinstance(settings, dict):
		raise ValueError('--core-settings must be a JSON object.')
	return settings


def write_core_settings(
	profile: Path, settings: dict[str, object] | None,
) -> None:
	if settings is None:
		return
	settings_path = Path(profile).joinpath(*CORE_SETTINGS_PATH)
	settings_path.parent.mkdir(parents=True, exist_ok=True)
	settings_path.write_text(
		json.dumps(settings, indent=2), encoding='utf-8')

