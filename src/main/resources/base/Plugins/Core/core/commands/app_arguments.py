"""Arguments prompt shared by Open With apps and File Type Actions."""
from core.text_editor import parse_arguments
from fman import show_alert, show_input


ARGUMENTS_PROMPT = 'Arguments ({file} is the file; it is added last when missing):'


def ask_arguments(default_text: str) -> list[str] | None:
	text = show_input(ARGUMENTS_PROMPT, default_text)
	if text is None:
		return None
	try:
		return parse_arguments(text)
	except (ValueError, OSError) as error:
		show_alert('Could not read the arguments: %s' % error)
		return None
