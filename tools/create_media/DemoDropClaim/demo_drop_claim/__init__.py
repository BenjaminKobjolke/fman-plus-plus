"""Demo 29 only: claims drops of files named a-claimed* so Core's copy never starts."""

from fman import DirectoryPaneListener, show_status_message
from fman.url import basename

CLAIM_PREFIX = 'a-claimed'


class ClaimDemoDrop(DirectoryPaneListener):
	def on_files_dropped(
		self, file_urls: list[str], dest_dir: str, is_copy_not_move: bool
	) -> bool:
		if not all(basename(url).startswith(CLAIM_PREFIX) for url in file_urls):
			return False
		show_status_message(
			'DemoDropClaim handled the drop - Core did not copy it.', 10
		)
		return True
