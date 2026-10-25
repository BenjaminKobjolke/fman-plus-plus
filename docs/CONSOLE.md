# Plugin console

The console gives plugin developers one place to see plugin messages, printed
output and errors. Open it from the command palette with **Show console** to
use a live pane, or **Show console window** to use a separate live window.
Both views share the same in-memory log and update as entries arrive.

## Logging

Plugin `print()` output is captured and remains forwarded to the original
stdout or stderr when that stream exists. Call `fman.log(*args)` to add a
message explicitly; its arguments are converted to strings, joined with
spaces, and followed by a newline. The log retains the newest 2000 entries and
is cleared when fman exits.

Entries appear in these forms:

- Printed text and `fman.log()` messages appear as written.
- Plugin errors have a timestamped headline followed by the pruned traceback:
  `--- HH:MM:SS <headline> ---`.
- Prompt input is echoed with `>>>` for a new statement and `...` for a
  continuation line.

## Python prompt

The prompt executes each entered line on a worker thread. The input is disabled
while code runs. Its namespace contains `fman`, `window` and `pane`, referring
to the fman API, the current window and the pane showing the console. Use a
blank continuation line to finish a multi-line statement. Up and Down recall
the prompt's input history; Escape closes the pane console or console window.

## Plugin error alert

When a plugin raises an error, fman writes its headline and traceback to the
console and shows a short alert without the error details. The alert offers:

- **Dismiss** closes the alert.
- **Open in console** opens the console in the active pane (or the first pane
  when no pane has focus).
- **Copy error** copies the headline and full traceback to the clipboard.
