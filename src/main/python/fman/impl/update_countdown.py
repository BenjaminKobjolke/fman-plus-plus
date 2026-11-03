"""Show the update countdown on fman's main thread."""

from fman import _get_ui
from fman.impl.countdown import Countdown
from fman.impl.util.qt.thread import run_in_main_thread

@run_in_main_thread
def show_update_countdown(text_template, seconds):
	main_window = _get_ui()
	countdown = Countdown(main_window, text_template, seconds)
	countdown.setStandardButtons(Countdown.Ok | Countdown.Cancel)
	countdown.button(Countdown.Ok).setText('Update now')
	countdown.setDefaultButton(Countdown.Cancel)
	return main_window.exec_dialog(countdown) == Countdown.Ok
