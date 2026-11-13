"""Extension-based file coloring and its Core Settings.json options."""
import fnmatch
from collections import namedtuple

from core.settings import get_setting, SETTINGS_FILE
from fman.impl.themes import (
	FILE_ARCHIVE_FG, FILE_IMAGE_FG, FILE_MEDIA_FG, FILE_PROGRAM_FG
)
from fman.url import basename


FILE_COLORING_SETTING = 'file_coloring'
FILE_COLOR_RULES_SETTING = 'file_color_rules'
DEFAULT_FILE_COLORING = False
DEFAULT_FILE_COLOR_RULES = [
	{
		'patterns': [
			'*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp', '*.svg'
		],
		'color': FILE_IMAGE_FG,
	},
	{
		'patterns': ['*.zip', '*.7z', '*.rar', '*.tar', '*.gz'],
		'color': FILE_ARCHIVE_FG,
	},
	{
		'patterns': [
			'*.mp3', '*.wav', '*.flac', '*.mp4', '*.mkv', '*.avi', '*.mov'
		],
		'color': FILE_MEDIA_FG,
	},
	{
		'patterns': ['*.exe', '*.bat', '*.cmd', '*.ps1', '*.msi'],
		'color': FILE_PROGRAM_FG,
	},
]
FileColorOptions = namedtuple('FileColorOptions', ('enabled', 'rules'))


def _clean_rules(value):
	if not isinstance(value, list):
		return None
	return [
		rule for rule in value
		if (
			isinstance(rule, dict)
			and isinstance(rule.get('patterns'), list)
			and bool(rule['patterns'])
			and all(
				isinstance(pattern, str) and pattern for pattern in rule['patterns']
			)
			and isinstance(rule.get('color'), str)
		)
	]


def load_options():
	enabled = get_setting(
		SETTINGS_FILE, FILE_COLORING_SETTING, DEFAULT_FILE_COLORING
	)
	rules = get_setting(
		SETTINGS_FILE, FILE_COLOR_RULES_SETTING, DEFAULT_FILE_COLOR_RULES
	)
	clean_rules = _clean_rules(rules)
	return FileColorOptions(
		enabled if type(enabled) is bool else DEFAULT_FILE_COLORING,
		clean_rules if clean_rules is not None else DEFAULT_FILE_COLOR_RULES,
	)


def make_colorer(rules):
	"""Match the first case-insensitive filename pattern and return its color."""
	valid_rules = [
		(rule['patterns'], rule['color']) for rule in (_clean_rules(rules) or ())
	]

	def colorer(url):
		name = basename(url).lower()
		for patterns, color in valid_rules:
			if any(fnmatch.fnmatch(name, pattern.lower()) for pattern in patterns):
				return color
		return None

	return colorer


def is_enabled():
	return load_options().enabled


def apply(pane):
	options = load_options()
	pane.set_file_coloring(
		make_colorer(options.rules) if options.enabled else None
	)
