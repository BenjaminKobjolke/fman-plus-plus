# Status bar

The strip along the bottom of fman's window. It shows one line of text at a
time — the last message fman or a plugin had to say — and nothing else. It can
be turned off from the [command palette](COMMAND_PALLETTE.md), and stays off
across restarts. Each pane can also show its own short-lived message line
under its content; see [Pane status lines](#pane-status-lines).

## What it shows

The window-wide bar has a single message slot, left-aligned. Whatever wrote
last wins.

| When | Message |
|------|---------|
| Startup | `v1.7.8 ready.` — or `Updated to v1.7.8. Changelog` after a version change, where *Changelog* is a clickable link |
| Copy / cut to clipboard | `Copying foo.txt`, `Cutting foo.txt and 3 other files`, `Copied C:\dir\foo.txt to the clipboard` |
| Reloading plugins | `Reloaded 2 plugins.` |
| Saving in the [text viewer](views/TEXT_VIEWER.md#editing) | `Saved`, `Saved as <path>`, `Could not save: <reason>` |
| Auto-reload / tail toggles | `Auto-reload on`, `Tail mode on`, `Auto-reload off`, `File changed on disk (not reloaded)` |
| Any other [viewer](viewers/FILE_VIEWERS.md#status-bar-feedback) action | `Reloaded from disk`, `Edit mode`, `Font size 12`, `Zoom 125%`, `Paused`, the name of the file Next/Previous landed on, ... (also shown in that viewer's pane line by default) |
| [Viewer navigation](viewers/FILE_VIEWERS.md) | `Advance only for same type: on`, `No further file to view` |
| Long-running work | a "doing X…" line for as long as the work runs, then cleared |
| Nothing recent | `Ready.` |

Messages either sit there until something replaces them, or carry a timeout
after which the bar falls back to `Ready.` — 2–5 seconds for the routine ones,
longer for hints.

A message may contain HTML links (the changelog one does); they open in the
external browser.

When incognito mode is on, a permanent **Incognito** marker appears at the
right side of the bar. It has its own slot, so later status messages do not
replace it. Turning incognito on or off also shows `Incognito on.` or
`Incognito off.` in the message slot. The marker is hidden while the whole
status bar is hidden. See [Incognito mode](functions/go-to.md#incognito-mode)
for what the mode keeps out of saved history and session locations.

## Turning it off

Press **`Ctrl+Shift+P`** and run **"Toggle status bar"**. The bar disappears
immediately and the panes grow into the row it occupied — the window keeps its
size on screen. Running the command again brings it back.

| Command name        | Palette label     | Platform | Default key binding |
|----------------------|--------------------|-----------|----------------------|
| `toggle_status_bar`  | Toggle status bar  | all       | none (palette only)  |
| `toggle_incognito` | Toggle incognito mode | all | none (palette only) |

*statusbar*, *hide status bar*, *message bar*, *bottom bar* and *chrome* also
find the row — hidden keywords, so it still reads "Toggle status bar". See
[the command palette](COMMAND_PALLETTE.md#hidden-search-keywords).

Bind it to a key like any other command
(see [`docs/KEYBINDINGS.md`](KEYBINDINGS.md)):

```json
{ "keys": ["Ctrl+Alt+S"], "command": "toggle_status_bar" }
```

### Notes

- **Long messages are cut off at the window edge.** They never prevent the
  window from being made narrower.
- **Messages are not lost, just not drawn.** fman and plugins keep calling
  `show_status_message(...)` while the bar is hidden; the text is set on a
  widget nobody can see, and the latest one is there when you bring the bar
  back. Nothing errors, nothing queues up.
- **Hiding it is not the same as hiding the title bar.** The status bar is an
  ordinary child widget, so switching it off does not recreate the window and
  has none of the frameless-window caveats — the window stays draggable and
  closable. See [Toggle title bar](functions/window-bars.md).
- **The state survives a restart without a flash**, applied before the window
  is first shown, the same way the title bar and
  [window opacity](functions/window-opacity.md) are.

## Theming

The bar is styled through two tokens (see [`docs/THEMES.md`](THEMES.md)):

| Token                  | What it paints                                     |
|-------------------------|-----------------------------------------------------|
| `statusbar_bg_top`      | Top of the vertical background gradient             |
| `statusbar_bg_bottom`   | Bottom of it — falls back to `statusbar_bg_top`, so a flat bar means naming only the one token |

The text colour is `bright_fg` and the line above the bar is `border`; both
are shared with the rest of the chrome rather than being status-bar-specific.
Its font size is set in `Theme.css` under the `.statusbar` selector (8pt by
default, 11pt on macOS), which maps to `QStatusBar, QStatusBar QLabel`.

## Pane status lines

Each pane has a thin status line below its file list or mounted viewer. It is
hidden when empty, and each pane keeps its own message and timeout. Plugins can
send messages with `pane.show_status_message(text, timeout_secs=None)` and
clear them with `pane.clear_status_message()`; these methods are documented in
the [plugin API](PLUGINS_API.md#panes). A timed-out or cleared message hides the
line again.

By default a pane message appears both in that pane's line and in the
window-wide status bar. The two destinations have independent messages: a pane
message only clears the window bar when it still contains that same message,
so clearing an old pane message cannot erase newer window feedback. The
existing `fman.show_status_message(...)` API continues to write only to the
window-wide bar.

Both settings are enabled by default and persist across restarts:

| Setting key | Command | Effect when enabled |
|-------------|---------|---------------------|
| `pane_status_lines_visible` | `toggle_pane_status_lines` — Toggle pane status lines | Pane message lines are shown. When disabled, pane messages go to the window bar instead. |
| `pane_messages_in_status_bar` | `toggle_pane_messages_in_status_bar` — Toggle pane messages in status bar | Pane messages are copied to the window bar as well. This setting is ignored while pane lines are disabled. |

Both commands are available in the command palette and have no default key
binding. Pane messages reach the window bar when `pane_messages_in_status_bar`
is enabled or `pane_status_lines_visible` is disabled. The window-wide message
API and its behavior are unchanged.

### Pane line theming

Pane lines inherit the window status bar's appearance unless a theme overrides
their own tokens (see [`docs/THEMES.md`](THEMES.md)):

| Token | Inherits from | What it paints |
|-------|---------------|----------------|
| `pane_statusbar_bg_top` | `statusbar_bg_top` | Top of the pane line's gradient |
| `pane_statusbar_bg_bottom` | `pane_statusbar_bg_top` | Bottom of the gradient |
| `pane_statusbar_fg` | `bright_fg` | Text |
| `pane_statusbar_border` | `border` | Top edge |

The `.pane-statusbar` selector targets only pane lines. The existing
`.statusbar` selector still sets the font size for both the window bar and pane
lines; a later `.pane-statusbar` rule can set a pane-only font size.

### Where pane status lines live

- Widget and message routing: `fman/impl/widgets.py`
- Pane status mode and line widget: `fman/impl/pane_status.py`
- Public methods: `fman.DirectoryPane.show_status_message` and
  `fman.DirectoryPane.clear_status_message` in `fman/__init__.py`
- Settings and commands: `fman/impl/window_chrome.py` and
  `fman/impl/plugins/builtin.py`
- Viewer messages: `Plugins/Core/core/viewer_status.py`; the viewer passes its
  pane and keeps the existing three-second timeout
- Styles: `src/main/resources/base/styles.qss`

## Where it lives

- The widget: `fman/impl/widgets.py` — `MainWindow.__init__` builds the
  `QStatusBar` and the `QLabel` inside it (`setOpenExternalLinks(True)` is what
  makes the changelog link clickable, `setSizeGripEnabled(False)` removes the
  resize grip), plus `show_status_message` / `clear_status_message` and the
  single-shot `QTimer` behind `timeout_secs`
- The plugin API: `fman.show_status_message(text, timeout_secs=None)` and
  `fman.clear_status_message()` — see [`docs/PLUGINS_API.md`](PLUGINS_API.md).
  `core.commands.StatusMessage` is a context manager wrapping the pair for
  "show while this runs"
- The startup message: `fman/impl/session.py`
- The viewers' own messages: `Plugins/Core/core/viewer_status.py` —
  `viewer_status(pane, text)`, a 3-second-timeout wrapper every in-pane viewer
  reports through (see
  [`docs/viewers/FILE_VIEWERS.md`](viewers/FILE_VIEWERS.md#status-bar-feedback))
- Toggle command: `fman/impl/plugins/builtin.py` (`ToggleStatusBar`), beside
  `ToggleTitleBar`
- Show/hide on the widget: `MainWindow.set_status_bar_visible`
- State and persistence: `fman/impl/window_chrome.py` (`WindowChrome`), saved
  as `status_bar_visible` in `%APPDATA%/fman/Local/Settings.json`. The key is
  only written while the bar is hidden; a visible bar is the absence of the key
- Styling: `src/main/resources/base/styles.qss` (gradient, border, text
  colour), `src/main/resources/windows/os_styles.qss` (`min-height`), and
  `Plugins/Core/Theme.css` / `Theme (Mac).css` (font size)
