# File viewers

fman can show a file's contents **inside the active pane**, replacing the
file list until you close it — no external app launch, no waiting. This lets
you peek at (and, for text, quickly edit) a file without leaving fman.

## Opening a viewer

Put the cursor on a file and run **"View file"** from the
[command palette](../COMMAND_PALLETTE.md) (`view_file`), or
**"View file in other pane"** (`view_file_in_other_pane`) to open it in the
opposite pane and keep browsing. Neither has a default key binding — bind your
own if you want one. See
[`docs/functions/view-file.md`](../functions/view-file.md).

**"View file" picks the viewer by file type** — you don't choose:

| File type | Viewer | Recognized by |
|-----------|--------|----------------|
| Text-like (anything not image/video/binary) | [Text viewer](../views/TEXT_VIEWER.md) | fallback; binaries (NUL byte) alert instead |
| Images | [Image viewer](../views/IMAGE_VIEWER.md) | `.png .jpg .jpeg .gif .bmp .webp .ico .svg` |
| Video | [Video viewer](../views/VIDEO_VIEWER.md) | `.mp4 .m4v .mkv .webm .avi .mov .wmv .flv .mpg .mpeg .ogv .3gp .ts` |

## The three viewers at a glance

| | [Text](../views/TEXT_VIEWER.md) | [Image](../views/IMAGE_VIEWER.md) | [Video](../views/VIDEO_VIEWER.md) |
|-|------|-------|-------|
| Editable | Yes (UTF-8, untruncated) | No | No |
| Zoom | Font size | Scale + pan | — (fills pane) |
| Extras | auto-reload / tail mode, [`/` search](../views/TEXT_VIEWER.md#search) | animated GIFs play | play/pause, seek, volume (persists) |
| Backend | `QPlainTextEdit` | `QPixmap` / `QMovie` | [python-mpv / libmpv](../views/VIDEO_VIEWER.md#playback-backend) |

## Shared behaviour

All three viewers work the same way where it counts:

- **Close:** `Escape` / `Enter` / `Backspace` returns to the file list, cursor
  back on the same file. (Text edit mode with unsaved changes prompts first.)
- **Switch panes:** `Tab` / `Shift+Tab`, same as the file list. The viewer
  stays open; `Tab` back returns focus to it. (Text: view mode only — in edit
  mode `Tab` types a tab.)
- **Own command palette:** `Ctrl+Shift+P` opens a **viewer-scoped** palette,
  separate from the global one (which can't reach a viewer while the file list
  is hidden). It also offers pane commands marked for viewer use — see
  [`docs/COMMAND_PALLETTE.md`](../COMMAND_PALLETTE.md).
- **Shared file shortcuts:** F5 copies the viewed file to the other pane, F6
  moves it, and other suitable file-list shortcuts work too. Viewer-specific
  keys win; see [key bindings](../KEYBINDINGS.md#file-list-shortcuts-that-also-work-in-a-viewer).
- **Next / previous file:** **"Next file"** / **"Previous file"** in the viewer
  palette advance to the neighbouring file in the directory (following the
  pane's own sort order) without closing the viewer. A per-viewer
  **"Advance only for same type"** toggle (on by default) keeps e.g. the image
  viewer from stepping into a video; turn it off to walk across every viewable
  file, switching viewer type as needed. No default keys — bind your own (see
  [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings) for
  suggestions).
- **Delete / rename the file you're looking at:** **"Delete file"** moves it to
  the Recycle Bin (Trash on macOS/Linux) after the same confirmation the file
  list's Delete asks, and **"Rename file…"** prompts for a new name with the
  extension left unselected, then keeps the viewer open on the renamed file. A
  **"Close viewer after deleting"** toggle decides where a delete leaves you:
  on (the default) the file list comes back, off walks to the next file the way
  Next file does — so a folder of photos can be culled without leaving the
  viewer. Unlike the toggle above this one is global, shared by all three
  viewers. No default keys, deliberately.
- **Bindable keys:** viewer actions are pseudo-commands you rebind in a
  **separate** `Viewer Key Bindings (<OS>).json` — see
  [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings).
- **Editable palette rows:** `Shift+Enter` on any row of a viewer palette opens
  the same entry menu the global palette has — rename it, give it hidden search
  keywords, add or remove a key — writing to the viewer bindings file above.
  The exception is the zoom rows, which follow the global pane font-size
  shortcut and so edit `Key Bindings (<OS>).json` instead; see
  [`docs/COMMAND_PALETTE_KEYBINDINGS.md`](../COMMAND_PALETTE_KEYBINDINGS.md).
- **Status feedback:** every palette action confirms what it did —
  `Reloaded from disk`, `Edit mode`, `Saved`, `Font size 12`, `Zoom 125%`,
  `Paused`, `Renamed to notes.md`, or the name of the file Next/Previous
  landed on. These messages appear in the line at the bottom of the pane
  showing the viewer and, by default, in the window-wide
  [status bar](../STATUSBAR.md). It matters most where the pane looks unchanged
  afterwards: a reload of a file that hasn't changed on disk is otherwise
  invisible. Messages clear after 3 seconds. The exceptions are "Exit viewer"
  (the file list coming back says it) and
  [search](../views/TEXT_VIEWER.md#search), whose line stays up for as long as
  search mode is active. The two pane-message destinations can be configured
  with **Toggle pane status lines** and **Toggle pane messages in status bar**.
- **Per-pane, one at a time:** opening a viewer replaces whatever viewer is
  already open in that pane; the other pane is unaffected.
- **Theme-aware:** background/letterbox colors follow the active file-list
  palette, not a hardcoded value — see [`docs/THEMES.md`](../THEMES.md).

For per-viewer detail (usage, zoom, controls, limits, implementation) see each
viewer's own doc linked above.

## Adding your own

The three above are not special-cased: each is an `fman.Viewer` subclass in the
Core plugin (`Plugins/Core/core/viewers.py`), registered through the same
lookup a plugin's viewer uses. A plugin that subclasses `Viewer` inherits
everything on this page — the close keys, pane switching, the viewer palette,
next/previous-file, the same-type toggle and delete/rename. See
[Plugin API](../PLUGINS_API.md#viewers).
