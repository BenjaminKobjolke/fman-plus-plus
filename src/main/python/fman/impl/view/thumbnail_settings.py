"""Preview policy for files shown in a pane's thumbnail view."""

from dataclasses import dataclass
from fman import PLATFORM

PREVIEWS_IMAGES = 'images'
PREVIEWS_WINDOWS = 'windows'
LOCATIONS_LOCAL = 'local'
LOCATIONS_EVERYWHERE = 'everywhere'
MIN_SIZE = 48
MAX_SIZE = 512


@dataclass(frozen=True)
class ThumbnailSettings:
	size: int = 128
	previews: str = PREVIEWS_IMAGES
	locations: str = LOCATIONS_LOCAL
	image_extensions: tuple[str, ...] = ()

	def wants_preview(self, url: str) -> str | None:
		"""Return the preview reader kind for `url`, if policy allows one."""
		is_local = url.lower().startswith('file://')
		if (self.locations == LOCATIONS_EVERYWHERE or is_local) and \
				url.lower().endswith(self.image_extensions):
			return 'image'
		if (self.previews == PREVIEWS_WINDOWS and PLATFORM == 'Windows'
				and is_local):
			return 'shell'
		return None
