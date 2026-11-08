from fman import DirectoryPaneCommand
from fman.impl.util.qt.thread import run_in_main_thread

__all__ = ['ToggleCompactView']


class ToggleCompactView(DirectoryPaneCommand):
	aliases = ('Toggle compact view',)

	@run_in_main_thread
	def __call__(self):
		widget = self.pane._widget
		widget.set_compact_view(not widget.is_compact_view())
