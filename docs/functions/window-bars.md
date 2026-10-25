# Toggle title bar / Toggle menu bar

Turns off the window chrome fman does not need, from the
[command palette](../COMMAND_PALLETTE.md). Each toggles on its own, applies
immediately, and is remembered across restarts.

- **Toggle title bar** — the OS title bar around the window. Every platform.
- **Toggle menu bar** — fman's **Help** menu. **macOS only:** that menu is the
  only one fman has, and it exists only on macOS, where it lives in the system
  menu bar at the top of the screen rather than inside fman's window. On
  Windows and Linux fman has no menu at all, so the command is not registered
  and does not appear in the palette.

The bars and messages below the panes have three commands on every platform —
see [`docs/STATUSBAR.md`](../STATUSBAR.md):

| Command | What it controls |
|---------|------------------|
| `toggle_status_bar` | The window-wide message strip at the bottom |
| `toggle_pane_status_lines` | The message line under each pane |
| `toggle_pane_messages_in_status_bar` | Whether pane messages are also copied to the window bar |

Their settings persist across restarts. The pane commands do not share the
title-bar caveats described here.

The two are never stacked inside the window: hiding the title bar does not
uncover a menu row below it, because on the platforms where the title bar sits
on the window there is no menu row at all.

## Usage

1. Press **`Ctrl+Shift+P`** and run **"Toggle title bar"** — or, on macOS,
   **"Toggle menu bar"**.
2. The bar disappears right away. Running the same command again brings it
   back.

There is no "on/off" list to pick from: each command flips the bar it names.

## Commands

| Command name       | Palette label    | Platform | Default key binding |
|---------------------|-------------------|-----------|----------------------|
| `toggle_title_bar`  | Toggle title bar  | all       | none (palette only)  |
| `toggle_menu_bar`   | Toggle menu bar   | macOS only | none (palette only) |

*Frameless*, *borderless*, *window frame* and *caption* find the title bar
one; *help menu*, *hide menu* and *chrome* find the other where it exists.
They are hidden keywords, so the rows still read "Toggle title bar" and
"Toggle menu bar" —
see [the command palette](../COMMAND_PALLETTE.md#hidden-search-keywords).

Bind them to keys in `Key Bindings.json` like any other command
(see [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md)):

```json
{ "keys": ["Ctrl+Alt+T"], "command": "toggle_title_bar" },
{ "keys": ["Ctrl+Alt+M"], "command": "toggle_menu_bar" }
```

## Notes

- **A window with no title bar has no close button and cannot be dragged.**
  It is a real frameless window, so the OS draws nothing to grab: no drag,
  no double-click-to-maximize, no edge resizing, no snapping to a screen
  half. `Ctrl+Shift+P` → *Toggle title bar* is the way back, and it is worth
  binding a key before you first turn the bar off. While the bar is gone,
  *Center window* still moves the window
  (see [the command palette](../COMMAND_PALLETTE.md)), as does the OS's own
  move shortcut (`Alt+Space`, then `M`, on Windows).
- **On macOS the menu bar is the system one**, at the top of the screen rather
  than inside fman's window. *Toggle menu bar* hides the **Help** menu's own
  `QAction` there, which is what Qt propagates to the native bar — hiding the
  `QMenuBar` itself would do nothing. *Toggle title bar* works everywhere.
- **The title bar toggle recreates the native window.** That is what Qt does
  when window flags change; fman restores the window's position and its
  [opacity](window-opacity.md) around it, because the recreated window would
  otherwise come back at the wrong spot and, on Windows, fully opaque — the
  same `WS_EX_LAYERED` mechanism described in
  [Set window opacity](window-opacity.md).
- **The window keeps the screen space it had.** Hiding the title bar grows the
  panes into the row the bar occupied instead of shrinking the window by it
  (the client area is set to the old *frame* geometry); showing it again
  restores the framed geometry from before the toggle, so the window is back
  to exactly the size it started at. That remembered geometry lives on the
  widget, so a restart with the bar already hidden starts from whatever
  geometry it restores, not from a pre-toggle one.
- **The state survives a restart without a flash.** Both bars are applied
  before the window is first shown, so a hidden bar is never briefly
  visible at startup — the same ordering [Set window opacity](window-opacity.md)
  relies on.
- **Hiding the title bar hides the window title with it** — the two-pane path
  string described in
  [Window title and bars](../WINDOW_TITLE_AND_BARS.md). fman still sets it,
  nothing draws it, and it returns unchanged when the bar does.
- **The two bars never sit on top of each other.** On macOS the Help menu is
  in the system bar, not below fman's title bar; on Windows and Linux there is
  no menu. So hiding the title bar takes the topmost row away outright — the
  palette is then only reachable by its key binding.

## Where it lives

- Commands: `fman/impl/plugins/builtin.py` (`ToggleTitleBar`,
  `ToggleMenuBar`), beside `ToggleFullscreen`. `ToggleMenuBar` is registered
  only `if is_mac()` — `ApplicationCommand` has no `is_visible()`, so gating
  the registration is what keeps it out of the palette elsewhere
- The menu itself: `ApplicationContext.help_menu_actions`, which returns its
  three entries only on Mac, and `MainWindow._init_help_menu`, which builds
  nothing from an empty list
- State and persistence: `fman/impl/window_chrome.py` (`WindowChrome`)
- Application to the widget: `fman/impl/widgets.py`
  (`MainWindow.set_title_bar_visible` / `set_menu_bar_visible` — the latter
  hides `self._help_menu.menuAction()`), and `ApplicationContext.main_window`
  for the pre-`show()` pass
- Saved as `title_bar_visible` and `menu_bar_visible` in
  `%APPDATA%/fman/Local/Settings.json`, beside `theme` and `window_opacity`.
  A key is only written while its bar is hidden; a visible bar is the absence
  of the key
