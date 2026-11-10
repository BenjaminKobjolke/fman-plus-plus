from collections import namedtuple
from numbers import Real
from PyQt5.QtCore import Qt
import traceback


SHADE_TRANSPARENCY = 'transparency'
SHADE_TINT = 'tint'
SHADE_BOLD = 'bold'
SHADE_STYLES = (
	SHADE_TRANSPARENCY, SHADE_TINT, SHADE_BOLD
)

# Draw this row with a graded appearance.
ShadeRole = Qt.UserRole + 2
Shade = namedtuple('Shade', ('style', 'amount'))

_failed_shader_ids = set()


def safe_shade(shader, style, url):
	if shader is None:
		return None
	try:
		amount = shader(url)
	except Exception:
		# PyQt aborts the app on exceptions raised from a data() override.
		shader_id = id(shader)
		if shader_id not in _failed_shader_ids:
			_failed_shader_ids.add(shader_id)
			traceback.print_exc()
		return None
	if amount is None:
		return None
	if isinstance(amount, Real):
		return Shade(style, min(1, max(0, amount)))
	return None
