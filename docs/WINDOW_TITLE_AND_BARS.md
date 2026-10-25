# Window title and bars

What fman puts at the top of its window: the title, the OS title bar that
draws it, and — on macOS only — fman's own **Help** menu in the system menu
bar.

## Window title

The fman window title shows both panes' current paths, kept in sync as either
pane navigates.

### Format

```
fman - file manager - <left pane path> | <right pane path>
```

Example:

```
fman - file manager - C:\test | D:\GIT\BenjaminKobjolke\fman\debug
```

- A fixed `fman - file manager` prefix.
- Pane paths in **left, right** order (matches pane order everywhere else in
  fman, e.g. `window.get_panes()`), separated by ` | `.
- A pane whose path can't be rendered (e.g. `null://`) is skipped rather than
  shown as garbage; with zero renderable panes the title falls back to just
  the prefix.
- Updates live: navigating either pane (open a folder, go up, jump via the
  location bar, etc.) refreshes the whole title, not just that pane's segment.

### Notes

- This replaces the static title set by the core app (`fman`) once the main
  window is shown. There is no registration marker to fold in: this fork has
  no licensing (see `docs/PURCHASING.md`).

### Implementation

- `src/main/resources/base/Plugins/Core/core/commands/window.py` —
  `UpdateWindowTitle` (`DirectoryPaneListener`). Sets the title once on
  startup and again on every `on_path_changed`, mirroring the existing
  `InitHiddenFilesFilter` / `InitPaneFontSize` startup-listener pattern.
- `_format_window_title(paths)` is the pure string builder (prefix + join),
  kept separate from pane/Qt access so it's unit-testable without a running
  application. `_path_for_title(pane)` converts a pane's URL
  (`pane.get_path()`) to a human-readable path via `as_human_readable(...)`,
  swallowing any conversion error as a blank/skipped segment.
- `_refresh_window_title(window)` reads all panes via `window.get_panes()`
  and calls `window._widget.setWindowTitle(...)`. `DirectoryPaneListener`
  callbacks run off the Qt main thread
  (`ListenerWrapper._notify_listener_in_thread`), so this function is
  decorated with `@run_in_main_thread` — the same pattern already used by
  `ResetPaneFontSize` and `ShowOnlyActivePane`/`ShowAllPanes` in
  `core/commands/pane_view.py`.
- `src/main/resources/base/Plugins/Core/core/tests/commands/test_window.py`
  — `FormatWindowTitleTest` covers the pure title-building logic (no paths,
  blank paths skipped, one path, two paths).

## The bars above the panes

Both can be turned off, one at a time, from the command palette — and both
stay off across restarts:

| Command             | What it hides                                       |
|----------------------|------------------------------------------------------|
| `toggle_title_bar`   | The OS title bar: the title above, and the window frame with it |
| `toggle_menu_bar`    | fman's **Help** menu — **macOS only**, and in the system menu bar, not in fman's window |

There is no menu on Windows or Linux, so `toggle_menu_bar` is not registered
there and never shows up in the palette.

The bars and messages below the panes have three more commands:
`toggle_status_bar` hides the window-wide status bar,
`toggle_pane_status_lines` shows or hides the line under each pane, and
`toggle_pane_messages_in_status_bar` controls whether pane messages are copied
to the window bar. Their settings persist across restarts; see
[`docs/STATUSBAR.md`](STATUSBAR.md).

Hiding the title bar hides the title described above with it — the string is
still set, there is just nothing drawing it, and it comes back untouched when
the bar does. A window with no title bar cannot be dragged or closed with the
mouse, so read the caveats before turning it off.

Either way the window keeps the screen space it had: hiding the title bar
grows the panes into the row the bar occupied rather than shrinking the window
by it, and showing the bar again puts the window back at exactly the size it
was before the toggle.

Full write-up, including the settings keys and the frameless-window caveats:
[`docs/functions/window-bars.md`](functions/window-bars.md).
