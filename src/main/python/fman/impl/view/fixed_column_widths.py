"""Fixed-width targets for columns, addressing upstream issue #253."""

from typing import Dict, List, Sequence


def get_target_widths(
	names: Sequence[str], content_hints: Sequence[int],
	header_hints: Sequence[int],
	sample_widths: Dict[str, int], dragged: Dict[str, int], fixed: bool
) -> List[int]:
	"""Return column targets, keeping Name content-sized in either mode."""
	if len(names) != len(content_hints) or len(names) != len(header_hints):
		raise ValueError(
			'names, content_hints and header_hints must have equal lengths'
		)
	if not fixed:
		return [
			max(content, header)
			for content, header in zip(content_hints, header_hints)
		]

	targets = []
	for name, content_hint, header_hint in zip(names, content_hints, header_hints):
		if name == 'Name' or name.endswith('.Name'):
			targets.append(max(content_hint, header_hint))
			continue
		preferred = dragged.get(name, sample_widths.get(name, content_hint))
		targets.append(max(header_hint, preferred))
	return targets
