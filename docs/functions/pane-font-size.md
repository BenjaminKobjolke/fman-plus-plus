# Pane font size

Command palette entries, keyboard shortcuts, and Ctrl+wheel zoom the font size
of both file panes in and out on the fly, and reset it back to the theme's
original size.

## Usage

1. Press **Alt+Up** to make the text in both panes larger, **Alt+Down** to
   make it smaller. Both panes always change together.
2. Hold **Ctrl** and turn the mouse wheel over a file list to zoom one step per
   wheel notch. On a touchpad, partial vertical scroll deltas accumulate into
   whole steps. On Mac, hold **Cmd** instead.
3. Press **Ctrl+=** or **Ctrl++** to zoom in and **Ctrl+-** to zoom out on
   Windows and Linux. On Mac, use **Cmd+=**, **Cmd++**, or **Cmd+-**.
4. Open the command palette and search "font size" to run the same actions,
   plus **Reset font size** (palette-only, no default key binding).
5. The chosen size is remembered — it survives restarting fman.

This changes the **size** of the text, not the typeface. Which font
family the UI is drawn in is a separate, independent setting — see
[Select font](select-font.md) and [`docs/FONTS.md`](../FONTS.md).

This zooms the two file-list panes and the command palette. The
[text viewer](../views/TEXT_VIEWER.md#zoom)
has its own, independent zoom that reuses these same shortcuts (whatever
they're currently bound to) and adds matching palette entries scoped to the
viewer.

## Commands

| Command name               | Palette label      | Keywords                            | Default key binding |
|-----------------------------|---------------------|--------------------------------------|----------------------|
| `increase_pane_font_size`   | Increase font size  | zoom in, larger pane font, bigger    | `Alt+Up`; `Ctrl+=` / `Ctrl++` (Windows/Linux), `Cmd+=` / `Cmd++` (Mac) |
| `decrease_pane_font_size`   | Decrease font size  | zoom out, smaller pane font, smaller | `Alt+Down`; `Ctrl+-` (Windows/Linux), `Cmd+-` (Mac) |
| `reset_pane_font_size`      | Reset font size     | default font size, reset zoom        | none (palette only)  |

The other words listed under *Keywords* are hidden search terms: they find
the command in the palette without ever being shown. See
[the command palette](../COMMAND_PALLETTE.md#hidden-search-keywords).

These can be rebound in `Key Bindings.json` like any other command, e.g.:

```json
{ "keys": ["Ctrl+0"], "command": "reset_pane_font_size" }
```

## Notes

- The font size is stored in `Core Settings.json` under the `pane_font_size`
  key. Running **Reset font size** removes that key entirely rather than
  writing back a hard-coded default.
- The two file-list panes and the command palette are affected — the status
  bar, location bar and column headers keep their own font size. The palette
  grows by the same number of points as the pane text, so the palette stays
  three points larger at every zoom; **Reset font size** puts it back. Its
  result list keeps a seven-row minimum when the window has room, and shrinks
  as needed in a short window so the dialog stays inside it while showing at
  least one full row. Go To and text prompts with suggestions use the same
  list sizing.
- **Respects a custom theme.** If you have your own
  `Theme.css` (e.g. `%APPDATA%/fman/Plugins/User/Settings/Theme.css` on
  Windows) that sets a different base `font-size`, the first zoom press steps
  from *that* size, not from fman's built-in default. Resetting removes the
  override completely, so the pane goes back to rendering your theme exactly
  as authored.
- Font size is clamped between 6pt and 40pt; repeatedly zooming past either
  end has no further effect.
- **The icons zoom too.** Both panes' icons scale by the same proportion as
  the text, so `Alt+Up` zooms the whole file list rather than leaving small
  icons beside big text. They scale from whatever size *Set icon size* or the
  theme asks for — at `48`, zooming in grows them from 48 — and stop at
  fman's 12–64 range, so a long zoom stops the icons before it stops the
  text. **Reset font size** puts both back. See
  [Icons](../ICONS.md#it-follows-the-font-zoom).
- The zoom is **not** stored as an icon size of its own: it is derived from
  `pane_font_size`, so *Set icon size* keeps showing the size you picked.
- Ctrl+wheel only handles vertical wheel movement while Ctrl is held. Each
  120-unit wheel notch changes the pane zoom once; smaller touchpad deltas are
  accumulated, and the remainder resets when Ctrl is released. Horizontal-only
  and unmodified wheel events keep their normal Qt behavior.
- **The icon size also moves the row height**, so if the rows are taller than
  the font explains, that is where it comes from — see
  [Select icon set](select-icon-set.md). Unlike the font size, it is a theme
  property, not a `Core Settings.json` one.
- **`go_up` moved to Ctrl+Up on Windows and Linux.** Alt+Up was previously
  `go_up` (go to parent directory) on those two platforms. To free it for
  this feature, `go_up` is now bound to **Ctrl+Up** there instead. On Mac,
  `go_up` was already `Cmd+Up`, so nothing changed. `go_up` is still also
  available on **Backspace** on every platform.

## Implementation

- `src/main/resources/base/Plugins/Core/core/commands/pane_view.py` —
  `IncreasePaneFontSize`, `DecreasePaneFontSize`, `ResetPaneFontSize`
  (`DirectoryPaneCommand` subclasses), plus `InitPaneFontSize`
  (`DirectoryPaneListener`) which re-applies a saved size when fman starts
  (mirrors the existing `InitHiddenFilesFilter` pattern).
- **How the icons and the palette follow it:** the same three code paths call
  `_apply_zoom_scale`. It gives `fman.set_icon_scale` the current pane size
  divided by the theme's original pane size, so icons retain proportional
  scaling. It gives `fman.set_palette_font_offset` the rounded difference in
  points, so the palette grows by the same number of points as the panes.
  `Theme.set_font_offset` applies that offset to the item title, hint and
  description it paints by hand (`get_quicksearch_item_css`) and appends a
  `Quicksearch QLineEdit` font-size rule after the theme's own
  `.quicksearch-query` rule. Neither zoom is saved here, because
  `pane_font_size` already persists and is re-applied on startup; saving it
  twice would give one zoom two homes that could disagree.
- The zoom baseline is captured by `_remember_base_pane_font_size`, once
  per session, **before** any override stylesheet is set. After that the view
  reports the override, so the theme's own size is no longer readable — which
  is why `InitPaneFontSize` records it unconditionally, even when there is no
  saved size to apply.
- The font is changed by setting a **widget-local QSS stylesheet** directly on
  each pane's file view: `FileListView { font-size: Npt; }`. This is applied
  via `pane._widget._file_view.setStyleSheet(...)`. A type-selector rule set
  locally on the widget beats both the app-wide `* { font-size }` rule from
  `Theme.css` and any user theme that also relies on that same `*` selector —
  so zooming works regardless of which theme is active.
- The starting size (before any zoom has ever been applied) is read directly
  off the live pane via `QFontInfo(view.font()).pointSize()`, so it reflects
  whatever theme is currently loaded rather than a hard-coded constant.
- `src/main/resources/base/Plugins/Core/Key Bindings.json` — the two Alt+Up and
  Alt+Down default bindings above.
- `src/main/resources/base/Plugins/Core/Key Bindings (Windows).json` and
  `Key Bindings (Linux).json` bind Ctrl+=, Ctrl++, and Ctrl+- to the pane zoom
  commands; `Key Bindings (Mac).json` uses the matching Cmd shortcuts.
- `src/main/resources/base/Plugins/Core/Key Bindings (Windows).json` and
  `Key Bindings (Linux).json` — `go_up` rebound from `Alt+Up` to `Ctrl+Up`.
  `Key Bindings (Mac).json` was not touched (`go_up` was already `Cmd+Up`).
- **Why the platform files had to change too:** fman loads the base
  `Key Bindings.json` first, then the platform-specific file, and the
  platform file's bindings are checked *before* the base file's — first match
  wins (`Controller.handle_shortcut`, `controller.py:35-44`). So a base-file
  binding for a key a platform file already claims is silently shadowed on
  that platform; adding Alt+Up in the base file alone would not have worked
  on Windows/Linux.
- `src/main/resources/base/Plugins/Core/core/tests/test_font_size.py`
  — `ClampFontSizeTest` covers the pure step/clamp logic.
- The clamp logic (`clamp_font_size`, 6–40pt bounds) and the shortcut-lookup
  helpers (`get_shortcuts_for_command`, `format_shortcut_hint`) actually live
  in `core/font_size.py` and `core/key_bindings.py` respectively, imported by
  `core/commands/pane_view.py`, which aliases `clamp_font_size` back to
  `_clamp_font_size` so the moved bodies read as they always did. They were
  split out so the
  [text viewer's own zoom](../views/TEXT_VIEWER.md#zoom) could reuse them
  without a circular import (the Core command package imports
  `core/textviewer.py` at module load, via `core/commands/opening.py`, so
  the reverse import isn't possible).
- Likewise, `_get_saved_pane_font_size`/`_save_pane_font_size` are now thin
  wrappers over `core/settings.py`'s generic `get_setting`/`save_setting`
  (`json_name, key[, value]`) — extracted once the text viewer's own zoom
  needed the exact same "get/set one key in a JSON settings file, `None`
  clears it" pattern under a different key
  (`text_viewer_font_size` vs. `pane_font_size`).
- `src/main/python/fman/impl/util/qt/wheel_zoom.py` — `CtrlWheelZoom` converts
  vertical Ctrl-wheel deltas into signed, whole-notch zoom steps and retains
  partial touchpad deltas.
- `src/main/python/fman/impl/view/__init__.py` and
  `src/main/python/fman/impl/view/compact_view.py` — both file-list views expose
  `wheel_event_filter` and pass unhandled wheel input to Qt.
- `src/main/python/fman/impl/widgets.py` connects the pane's filter to
  `Controller.on_zoom_step` in `src/main/python/fman/impl/controller.py`, which
  runs the existing increase or decrease pane zoom command when available.
