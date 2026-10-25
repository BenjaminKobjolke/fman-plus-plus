# Window functions

Everything that changes fman's **window itself** rather than what is inside
it: how much of it you see, how solid it is, and where it sits on the screen.
Each function has its own page with the settings keys and caveats — this one
is the map.

None of these have a default key binding. They are all reached from the
[command palette](COMMAND_PALLETTE.md) (`Ctrl+Shift+P`), and all of them
except *Center window* are remembered across restarts.

| Command | What it does | Details |
|---------|--------------|---------|
| `toggle_title_bar` | Hides the OS title bar and the window frame with it | [window-bars.md](functions/window-bars.md) |
| `toggle_menu_bar` | Hides fman's **Help** menu — **macOS only** | [window-bars.md](functions/window-bars.md) |
| `toggle_status_bar` | Hides the message strip along the bottom | [STATUSBAR.md](STATUSBAR.md) |
| `toggle_pane_status_lines` | Shows or hides the message line under each pane | [STATUSBAR.md](STATUSBAR.md#pane-status-lines) |
| `toggle_pane_messages_in_status_bar` | Copies pane messages to the window status bar | [STATUSBAR.md](STATUSBAR.md#pane-status-lines) |
| `set_window_opacity` | Makes the whole window see-through | [window-opacity.md](functions/window-opacity.md) |
| `center_window` | Puts the window back in the middle of its screen | [below](#center-window) |
| `minimize` | Minimizes the window | — |

The **dim behind dialogs** is the odd one out: it has no command, because it
is not something you switch on. It is a theme color — see
[Dimming behind dialogs](#dimming-behind-dialogs).

## Chrome: the bars around the panes

The title bar, the macOS menu bar and the status bar each toggle on their own
and each stay off across restarts, sharing one persistence mechanism
(`WindowChrome`). The pane status commands configure the per-pane message lines
and whether their messages are copied to the window status bar; see
[Pane status lines](STATUSBAR.md#pane-status-lines).

Two things worth knowing before hiding the title bar:

- A frameless window **cannot be dragged or closed with the mouse**. Read the
  caveats in [window-bars.md](functions/window-bars.md) first.
- The window keeps the screen space either way: hiding a bar grows the panes
  into the row it occupied rather than shrinking the window, and showing it
  again restores the exact previous size.

The window *title* itself — the format, and what happens to it while the bar
is hidden — is [WINDOW_TITLE_AND_BARS.md](WINDOW_TITLE_AND_BARS.md).

## Opacity: how solid the window is

`set_window_opacity` offers **Theme default**, then `100%` down to `70%`. The
whole window fades, text included; fman does not do background-only
translucency, and dialogs are separate windows that stay opaque.

**Theme default** is the way back to letting the theme decide — not `100%`,
which pins the window opaque under every theme, including one that ships
translucent. A theme sets its own value with the `opacity` key
([THEMES.md](THEMES.md#opacity)); your choice wins over it and survives a
theme switch.

## Dimming behind dialogs

While a modal dialog is open — the [command palette](COMMAND_PALLETTE.md),
prompts, alerts, the file-open dialog — fman lays a **scrim** over the main
window. The dialog then reads against the file list instead of competing with
it.

This works *because* of how opacity does not: dialogs are top-level windows of
their own, so nothing applied to the main window reaches them. Dim the main
window and the dialog keeps its full contrast.

- It is the `scrim_bg` color token, and its **alpha byte is the strength**.
  `#80000000` (the default) is 50% black, `#40000000` a quarter,
  `#00000000` no dim at all.
- The **progress dialog is excluded**. A copy can run for minutes, and a
  window dimmed that long costs more than the contrast is worth.
- There is no command and no setting: a theme owns it, like any other color.
  See [Dimming behind dialogs](THEMES.md#dimming-behind-dialogs).

## Center window

`center_window` puts fman back in the middle of the screen it is already on.

- Centered within the screen's *available* area, so a taskbar does not push
  the window off-center.
- On multiple monitors it stays on the monitor it was on rather than jumping
  to the primary one.
- Nothing is remembered — it is a one-shot move, not a mode.

Also found by *center window on screen*, *move window to center* and
*middle* ([hidden keywords](COMMAND_PALLETTE.md#hidden-search-keywords)).
Bind it like any other command
([KEYBINDINGS.md](KEYBINDINGS.md)):

```json
{ "keys": ["Ctrl+Alt+C"], "command": "center_window" }
```

## Implementation

- `src/main/resources/base/Plugins/Core/core/commands/window.py` —
  `CenterWindow`, `Minimize` and the chrome toggles;
  `src/main/resources/base/Plugins/Core/core/commands/theme.py` — the
  opacity picker (`SetWindowOpacity`).
- `src/main/python/fman/impl/widgets.py` — `MainWindow` and `Scrim`; the
  scrim is applied in `exec_dialog`, which is also where the comment lives
  explaining why dialogs never inherit the window's opacity.
- `src/main/resources/base/styles.qss` — the `Scrim` rule that gives it its
  `$scrim_bg` color.
