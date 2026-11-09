"""Edit Total Commander's per-file comments."""
from core.commands.columns import _apply_column_visibility
from core.commands.util import NO_SELECTION, is_file_url
from core.descript_ion import get_comment, set_comment
from core.panes import reload_panes
from fman import (
	DirectoryPaneCommand, show_alert, show_status_message, show_text_input,
	translate,
)
from fman.localization_keys import (
	FILE_COMMENT_LOCAL_ONLY, FILE_COMMENT_SAVE_FAILED,
	FILE_COMMENT_TITLE, FILE_COMMENT_TITLE_MULTIPLE,
)
from fman.url import basename

__all__ = ['EditComment']

_LOCAL_ONLY = translate(FILE_COMMENT_LOCAL_ONLY)
_SAVE_FAILED = translate(FILE_COMMENT_SAVE_FAILED)
_TITLE = translate(FILE_COMMENT_TITLE)
_TITLE_MULTIPLE = translate(FILE_COMMENT_TITLE_MULTIPLE)


class EditComment(DirectoryPaneCommand):
	aliases = ('Edit comment',)

	def __call__(self):
		urls = self.get_chosen_files()
		if not urls:
			show_alert(NO_SELECTION)
			return
		if any(not is_file_url(url) for url in urls):
			show_status_message(_LOCAL_ONLY)
			return

		comments = [get_comment(url) for url in urls]
		default = comments[0] if comments[0] is not None and all(
			comment == comments[0] for comment in comments
		) else ''
		if len(urls) == 1:
			title = _TITLE % basename(urls[0])
		else:
			title = _TITLE_MULTIPLE % len(urls)
		text = show_text_input(title, default)
		if text is None:
			return
		try:
			set_comment(urls, text)
		except OSError as error:
			show_alert(_SAVE_FAILED % error)
			return

		window = self.pane.window
		for pane in window.get_panes():
			_apply_column_visibility(pane)
		reload_panes(window)
