from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import url2pathname

from fman import DirectoryPaneListener


class ClaimDrops(DirectoryPaneListener):
	def on_files_dropped(
		self, file_urls: list[str], dest_dir: str, is_copy_not_move: bool
	) -> bool:
		destination = Path(url2pathname(urlsplit(dest_dir).path))
		lines = ['%s\t%s' % (
			Path(url2pathname(urlsplit(url).path)).name, is_copy_not_move)
			for url in file_urls]
		(destination / 'claimed_drop.txt').write_text(
			'\n'.join(lines) + '\n', encoding='utf-8')
		return True
