"""Copy or move files to the other pane without a destination prompt.

These commands implement upstream issue #437. The destination is fixed to the
other pane, while conflicts still use the normal overwrite dialog.
"""
from core.commands.transfer import Copy, Move
from core.commands.util import NO_SELECTION

import fman


class _SkipDestinationPrompt:
	@classmethod
	def _confirm_tree_operation(cls, files, dest_dir, ui=fman, fs=fman.fs):
		if not files:
			ui.show_alert(NO_SELECTION)
			return
		if cls._is_into_itself(files, dest_dir, ui, fs):
			return
		return dest_dir, None

	@classmethod
	def _verb(cls):
		return cls.__name__[len('Force'):].lower()


class ForceCopy(_SkipDestinationPrompt, Copy):
	aliases = ('Force copy',)


class ForceMove(_SkipDestinationPrompt, Move):
	aliases = ('Force move',)


__all__ = ['ForceCopy', 'ForceMove']
