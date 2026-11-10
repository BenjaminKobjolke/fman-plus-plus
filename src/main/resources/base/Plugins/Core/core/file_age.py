"""Built-in file-age shader and its Core Settings.json options."""
from collections import namedtuple
from datetime import datetime
from math import isfinite, log1p
from numbers import Real

from core.settings import get_setting, SETTINGS_FILE
from fman.fs import query


FILE_AGE_SHADING_SETTING = 'file_age_shading'
FILE_AGE_SCALE_SETTING = 'file_age_scale'
FILE_AGE_STYLE_SETTING = 'file_age_style'
FILE_AGE_FULL_DAYS_SETTING = 'file_age_full_days'

DEFAULT_FILE_AGE_SHADING = False
DEFAULT_FILE_AGE_SCALE = 'log'
DEFAULT_FILE_AGE_STYLE = 'transparency'
DEFAULT_FILE_AGE_FULL_DAYS = 365
FILE_AGE_SCALES = ('log', 'steps')
FILE_AGE_STYLES = ('transparency', 'tint', 'bold')

FileAgeOptions = namedtuple(
	'FileAgeOptions', ('enabled', 'scale', 'style', 'full_days')
)


def modified_datetime(url):
	return query(url, 'modified_datetime')


def _valid_full_days(value):
	return isinstance(value, Real) and not isinstance(value, bool) \
		and isfinite(value) and value > 0


def load_options():
	enabled = get_setting(
		SETTINGS_FILE, FILE_AGE_SHADING_SETTING, DEFAULT_FILE_AGE_SHADING
	)
	scale = get_setting(
		SETTINGS_FILE, FILE_AGE_SCALE_SETTING, DEFAULT_FILE_AGE_SCALE
	)
	style = get_setting(
		SETTINGS_FILE, FILE_AGE_STYLE_SETTING, DEFAULT_FILE_AGE_STYLE
	)
	full_days = get_setting(
		SETTINGS_FILE, FILE_AGE_FULL_DAYS_SETTING, DEFAULT_FILE_AGE_FULL_DAYS
	)
	return FileAgeOptions(
		enabled if type(enabled) is bool else DEFAULT_FILE_AGE_SHADING,
		scale if scale in FILE_AGE_SCALES else DEFAULT_FILE_AGE_SCALE,
		style if style in FILE_AGE_STYLES else DEFAULT_FILE_AGE_STYLE,
		full_days if _valid_full_days(full_days)
		else DEFAULT_FILE_AGE_FULL_DAYS
	)


def age_amount(age_days, scale, full_days):
	"""Return a clamped age amount from fresh (0) to fully shaded (1)."""
	age_days = max(0, age_days)
	if scale == 'steps':
		if age_days < 1:
			return 0
		if age_days < 7:
			return 1 / 3
		if age_days < 30:
			return 2 / 3
		return 1
	if scale == 'log':
		return min(1, log1p(age_days) / log1p(full_days))
	return 0


def make_age_shader(options):
	"""Build a local-file shader using modified time; remote URLs stay unshaded."""
	if not options.enabled:
		return None

	def shader(url):
		if not url.startswith('file://'):
			return None
		try:
			modified = modified_datetime(url)
		except Exception:
			return None
		if modified is None:
			return None
		now = datetime.now(modified.tzinfo) if modified.tzinfo else datetime.now()
		age_days = max(0, (now - modified).total_seconds() / 86400)
		if options.style == 'bold':
			return 0 if age_days < 1 else 1
		return age_amount(age_days, options.scale, options.full_days)

	return shader


def is_enabled():
	return load_options().enabled


def apply(pane):
	options = load_options()
	if options.enabled:
		pane.set_file_shading(make_age_shader(options), options.style)
	else:
		pane.set_file_shading(None, None)
