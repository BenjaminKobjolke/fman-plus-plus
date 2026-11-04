from fman import DirectoryPaneCommand

__all__ = ['ToggleCompactView']


class ToggleCompactView(DirectoryPaneCommand):
	aliases = ('Toggle compact view',)

	def __call__(self):
		widget = self.pane._widget
		widget.set_compact_view(not widget.is_compact_view())
