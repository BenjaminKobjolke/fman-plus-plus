"""Sizing rules shared by quicksearch and prompt text."""


TEXT_STEP_PTS = 2


def apply_text_sizes(query, header, footer=None):
	query.ensurePolished()
	pts = query.font().pointSizeF()
	header.setStyleSheet('font-size: %gpt;' % (pts + TEXT_STEP_PTS))
	if footer is not None:
		footer.setStyleSheet(
			'font-size: %gpt;' % max(1, pts - TEXT_STEP_PTS)
		)
