"""Per-pane mixed file and folder sorting, persisted in Panes.json.

The palette command toggles the choice. The listener applies it at startup
because pane commands are created lazily.
"""
from core.commands.hidden_files import _get_pane_info
from fman import DirectoryPaneCommand, DirectoryPaneListener, save_json, \
	show_status_message


__all__ = ['InitMixedSorting', 'ToggleMixedSorting']


def _is_mixing(pane):
	return _get_pane_info(pane).get('mix_files_and_folders', False)


class ToggleMixedSorting(DirectoryPaneCommand):
	aliases = ('Toggle mixed file and folder sorting',)

	def __call__(self):
		value = not _is_mixing(self.pane)
		_get_pane_info(self.pane)['mix_files_and_folders'] = value
		# Flush now so reloading plugins cannot restore the previous preference.
		save_json('Panes.json')
		self.pane._set_mix_dirs(value)
		self.pane.reload()
		message = 'Files and folders sorted together' if value else \
			'Folders sorted first'
		show_status_message(message, timeout_secs=3)


class InitMixedSorting(DirectoryPaneListener):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if _is_mixing(self.pane):
			self.pane._set_mix_dirs(True)
		# shortcut: no reload here, so a Core plugin reload with an already open
		# location keeps the old order until the next refresh or navigation.
