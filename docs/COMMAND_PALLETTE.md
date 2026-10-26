# Command palette

fman's command palette is a fuzzy-search picker for running any command by
name instead of hunting for a key binding. Type part of a command's name (or
one of its hidden keywords, below), pick from the filtered list, press Enter.

## The global command palette

- **Open it:** `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS) —
  the `command_palette` command (see [`docs/KEYBINDINGS.md`](KEYBINDINGS.md)).
- **Search:** matching is fuzzy — the typed characters just have to appear in
  order (`core/quicksearch_matchers.py`), so `vf` finds *View file*. Words
  after a space match on word boundaries first, then anywhere.
- **Word order doesn't matter:** space-separated words are also matched in any
  order, so `panes show` finds *Show all panes* just like `show panes` does.
  In-order and word-boundary matches still rank first; any-order matches fall
  to the bottom of the list.
- **Shortcut hints:** each entry shows the key it's currently bound to (if
  any), read live from the merged `Key Bindings.json` — rebind a command and
  the hint updates.
- **Remembers your last pick:** reopening the palette pre-selects the command
  you last ran, so repeating an action is Open → Enter.
- **Scope:** lists every command visible for the active pane plus global
  application commands. Only commands the pane marks visible show up.
- **It zooms with the panes:** [Increase / Decrease font
  size](functions/pane-font-size.md) scales the palette's own text by the same
  factor it scales the panes and their icons by, and **Reset font size** puts
  it back. The palette's base size is the theme's, in `Theme.css` — see
  [`docs/THEMES.md`](THEMES.md#themecss-fonts-padding-and-user-overrides).
- **The window dims behind it:** the palette is a window of its own, so it
  keeps full contrast while the file list behind it is covered by a scrim.
  How dark that scrim is, is the theme's `scrim_bg` — see
  [`docs/THEMES.md`](THEMES.md#dimming-behind-dialogs).

Commands worth knowing about that have no default key binding, so the
palette is the only way to reach them:

- **Select theme** — switch fman's colors, applied immediately. See
  [`docs/functions/select-theme.md`](functions/select-theme.md).
- **Select icon set** — swap the OS file icons for a set such as Material,
  with **Set icon size** to change how big they are drawn and **Set icon
  color** to recolor them (also found by *icon tint*, *recolor icons*,
  *colorize icons*). See
  [`docs/functions/select-icon-set.md`](functions/select-icon-set.md) and
  [`docs/ICONS.md`](ICONS.md).
- **Select font** — pick the font family the whole UI is drawn in, with
  **Reset font** to hand the choice back to the theme (also found by
  *typeface*, *default font*, *clear font*). See
  [`docs/functions/select-font.md`](functions/select-font.md) and
  [`docs/FONTS.md`](FONTS.md).
- **Set window opacity** — make the window see-through, or hand the choice
  back to the theme. See
  [`docs/functions/window-opacity.md`](functions/window-opacity.md).
- **Toggle title bar** — hide the OS window frame, remembered across
  restarts. A frameless window cannot be dragged or closed with the mouse, so
  read the caveats first. Its sibling **Toggle menu bar** hides fman's *Help*
  menu, and only appears on macOS — that menu does not exist on Windows or
  Linux. See [`docs/functions/window-bars.md`](functions/window-bars.md).
- **Toggle status bar** — hide the message strip along the bottom of
  the window, remembered across restarts. The panes grow into the row
  it leaves behind; messages keep being set, nothing draws them (also
  found by *statusbar*, *message bar*, *bottom bar*). See
  [`docs/STATUSBAR.md`](STATUSBAR.md).
- **Toggle incognito mode** — stop counting folders opened for GoTo, return to
  the folders shown before the mode was enabled when turning it off, and keep
  those folders when quitting. The status bar shows a
  permanent marker while it is on; restarting turns it off (also found by
  *privacy*, *private*, *folder history* or *visit history*). See
  [`docs/functions/go-to.md`](functions/go-to.md#incognito-mode).
- **Go home** — opens your home directory, plus a sibling command per
  destination that is otherwise awkward to reach: **Go to desktop**,
  **Go to documents**, **Go to downloads**, **Go to AppData**, **Go to temp**,
  and on Windows **Go to local AppData**, **Go to ProgramData**, **Go to
  Program Files** and **Go to Program Files (x86)**. GoTo itself
  (`Ctrl+P`) reaches all of them by path — these give the hidden and
  OneDrive-relocated ones a name you can type instead. A destination this
  machine doesn't have is left out of the list. See
  [`docs/functions/go-to.md`](functions/go-to.md).
- **Follow shortcut** — Windows only, and only listed while the cursor is on
  a `.lnk` file: goes to the shortcut's destination instead of launching it
  (also found by *lnk*, *link target*, *destination*). A folder is opened; for
  a file, its folder is opened with the cursor on it. See
  [`docs/functions/follow-shortcut.md`](functions/follow-shortcut.md).
- **Center window** — puts fman back in the middle of the screen it is
  already on (also found by *center window on screen*, *move window to
  center*, *middle*). Centered within the *available* area, so the taskbar
  doesn't push it off-center, and on two monitors it stays on the monitor it
  was on. Bind it with
  `{ "keys": ["Ctrl+Alt+C"], "command": "center_window" }` — see
  [`docs/KEYBINDINGS.md`](KEYBINDINGS.md).

It searches the **file-list** widget only. While an in-pane viewer is open,
the file list is hidden, so the global palette can't reach the viewer — that's
why viewers ship their own.

## Hidden search keywords

A command is also findable by words that are **not** in its name. They live
in `Command Keywords.json` — a flat map of command name to search terms — and
are never displayed: typing *transparency* selects the row that still reads
**Set window opacity**.

```json
{
    "set_window_opacity": ["transparency", "opacity", "alpha"],
    "pack": ["zip", "7z", "tar", "compress"],
    "video_mute": ["sound", "volume", "audio"]
}
```

Press **Shift+Enter** on any palette row to add or delete that command's
keywords without leaving fman. The screens, the ranking rules and where your
edits are stored are in
[`docs/COMMAND_PALETTE_KEYWORDS.md`](COMMAND_PALETTE_KEYWORDS.md).

## Changing a command's shortcut

The same **Shift+Enter** menu offers *Change key bindings for "…"*: a list of
the shortcuts that currently run the command, where *Add shortcut…* records the
next combination you **press** and picking one offers *Remove*. Bindings take
effect immediately and are stored in your own `Key Bindings (<OS>).json` — see
[`docs/COMMAND_PALETTE_KEYBINDINGS.md`](COMMAND_PALETTE_KEYBINDINGS.md).

## Renaming a command

The same **Shift+Enter** menu offers *Rename to…*: call **Quit** *Exit* and the
palette lists **Exit**, while `quit` still finds it (the original name becomes
one of its keywords). *Reset name* puts fman's own name back. Renames are
stored in `Command Titles.json` — see
[`docs/COMMAND_PALETTE_KEYWORDS.md`](COMMAND_PALETTE_KEYWORDS.md#renaming-a-command).

## Viewers have their own palettes

Each in-pane [file viewer](viewers/FILE_VIEWERS.md) has a **separate,
viewer-scoped command palette**, also on **`Ctrl+Shift+P`**, but reaching
different commands — the ones that make sense for what you're viewing:

| Viewer | Palette entries (summary) |
|--------|----------------------------|
| [Text viewer](views/TEXT_VIEWER.md#editing) | Exit, Edit file, Save / Save as…, Reload / Revert, auto-reload & tail toggles, font-size zoom, Next/Previous file, Advance-same-type toggle, Delete file, Rename file…, Close-after-delete toggle, Copy / Move and other opted-in pane commands (view mode with a file), Find… / Find next / Find previous / Exit search mode |
| [Image viewer](views/IMAGE_VIEWER.md#zoom) | Zoom in/out, Fit to window, Actual size (100%), Next/Previous file, Advance-same-type toggle, Delete file, Rename file…, Close-after-delete toggle, Copy / Move and other opted-in pane commands, Exit |
| [Video viewer](views/VIDEO_VIEWER.md#controls) | Play/Pause, Restart, Mute/Unmute, Reset volume, Next/Previous file, Advance-same-type toggle, Delete file, Rename file…, Close-after-delete toggle, Copy / Move and other opted-in pane commands, Exit |

Notes:

- The viewer palette is built on the same `show_quicksearch` API as the
  global one, so it fuzzy-searches and shows shortcut hints the same way.
- The entry set changes with context — e.g. the text viewer shows different
  entries in view mode vs. edit mode, and *Exit search mode* only while its
  [search](views/TEXT_VIEWER.md#search) is on.
- Viewer-only rows are pseudo-commands bound in `Viewer Key Bindings (<OS>).json`.
  Opted-in pane command rows are real global commands whose shortcuts and
  Shift+Enter edits use `Key Bindings.json`. See
  [`docs/KEYBINDINGS.md`](KEYBINDINGS.md#viewer-specific-bindings).
