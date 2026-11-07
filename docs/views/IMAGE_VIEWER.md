# Image viewer

An in-pane viewer that shows an image directly inside the active pane,
replacing the file list until closed — the [text viewer](TEXT_VIEWER.md)'s
counterpart for image files. It exists so you can peek at a `.png`/`.jpg`/
`.gif`/etc. without leaving fman or waiting on an external image app to
launch. Always read-only.

## Usage

1. Put the cursor on an image file and run **"View file"** from the command
   palette — the same command as the text viewer; see
   [`docs/functions/view-file.md`](../functions/view-file.md) for how it
   picks which viewer to open. (**"View file in other pane"** opens the image
   viewer in the opposite pane instead.)
2. The image fills the active pane, in place of the file list, scaled to fit
   the pane by default.
3. Press **Escape**, **Enter**, or **Backspace** to close the viewer and
   return to the file list, with the cursor back on the same file.
4. Press **Tab** to switch to the other pane — same as the normal file list.
   The viewer stays open in this pane; pressing **Tab** again brings focus
   straight back to it.
5. Press **Ctrl+Shift+P** to open the viewer's own command palette (see
   below) instead of closing with Escape/Enter/Backspace.

Suitable file-list shortcuts such as F5 (Copy) also work here; see
[shared viewer shortcuts](../KEYBINDINGS.md#file-list-shortcuts-that-also-work-in-a-viewer).

## Zoom

The viewer has its own scale zoom, independent of the
[text viewer's font-size zoom](TEXT_VIEWER.md#zoom) and the file-list panes'
zoom ([pane font size](../functions/pane-font-size.md)):

1. The pane's **Increase font size** / **Decrease font size** shortcuts also
   zoom the image — the same shortcuts the text viewer reuses, so there's no
   separate binding to learn. Defaults are `Alt+Up` / `Alt+Down`, plus
   `Ctrl+=` / `Ctrl++` and `Ctrl+-` on Windows and Linux, or the matching
   `Cmd` shortcuts on Mac.
2. Hold **Ctrl** and turn the mouse wheel to zoom the image one step per
   vertical wheel notch; on Mac, hold **Cmd** instead. Partial touchpad deltas
   accumulate into whole steps. Without Ctrl/Cmd, the wheel scrolls normally.
3. The viewer's own command palette (Ctrl+Shift+P) has **Zoom in** /
   **Zoom out** (showing the same shortcut as a hint), plus **Fit to
   window** (which returns to fit mode) and **Actual size (100%)**.
4. The chosen scale is remembered — survives closing/reopening the viewer
   and restarting fman — until reset (or Fit to window) clears it back to
   fit mode.
5. Zooming in from fit mode steps from whatever scale is *currently on
   screen*, not a hardcoded value — so the image doesn't jump when you first
   zoom in.
6. Every step reports where it landed in the
   [status bar](../STATUSBAR.md) — `Zoom 125%`, or `Fit to window` — which is
   the only way to read the current scale as a number.

## Pan

Once zoomed in past the pane's size, scrollbars appear and the **arrow
keys** pan the image (they fall through to the underlying scroll area,
same as any scrollable widget). In fit mode there's nothing to pan — the
whole image is always visible.

## Behaviour

- **Read-only.** There's no edit mode — unlike the text viewer, an image
  can't be modified in place.
- **Animated GIFs play.** A `.gif` animates automatically while open;
  scaling (fit or explicit) applies to the animation, not just a static
  frame.
- **Photo orientation is respected.** JPEG photos follow their EXIF
  orientation. Qt does not read orientation from the other supported formats,
  including WebP, so they display as before.
- **Per-pane, one at a time.** Opening an image while a text viewer (or
  another image) is open in that pane replaces it, and vice versa — both
  share the same pane mount slot; the other pane is unaffected.
- **Follows the active theme.** The letterbox background matches the file
  list's actual palette color, not a hardcoded value — see
  [`docs/THEMES.md`](../THEMES.md).
- **Recognized extensions:** `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`,
  `.webp`, `.ico`, `.svg`. Anything else opens in the
  [text viewer](TEXT_VIEWER.md) instead.

## Bindable commands

Beyond zoom (already bindable via the pane font-size shortcut, above, and
still read from `Key Bindings (<OS>).json`), the viewer's other actions are
viewer-only pseudo-commands you can bind your own key to in your own
`Viewer Key Bindings (<OS>).json` — a **separate file**, see
[`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings). A
rebind always wins over the default key listed below.

| Command                | Default key            | Action                |
|-------------------------|------------------------|------------------------|
| `image_reset_zoom`      | *(none — palette only)* | Fit to window         |
| `image_actual_size`     | *(none — palette only)* | Actual size (100%)    |
| `viewer_close`          | Escape/Enter/Backspace | Close viewer           |
| `viewer_switch_panes`   | Tab                    | Switch panes           |
| `viewer_open_palette`   | Ctrl+Shift+P           | Open viewer command palette |
| `viewer_next_file` / `viewer_previous_file` | *(none — palette only)* | View next / previous file in the directory |
| `viewer_toggle_same_type_advance` | *(none — palette only)* | Toggle "advance only for same type" |
| `viewer_delete_file` | *(none — palette only)* | Move the image to the trash |
| `viewer_rename_file` | *(none — palette only)* | Rename the image, keeping it open |
| `viewer_toggle_close_after_delete` | *(none — palette only)* | Toggle whether a delete closes the viewer or goes to the next file |

Next/previous and the same-type toggle are **shared** across all three viewers
— see [File viewers](../viewers/FILE_VIEWERS.md#shared-behaviour) for how they
behave and [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings)
for suggested keys.

## Why it works while the file list is hidden

Same mechanism as the text viewer — see
[`docs/views/TEXT_VIEWER.md`#why-it-works-while-the-file-list-is-hidden](TEXT_VIEWER.md#why-it-works-while-the-file-list-is-hidden).
The image viewer reuses the identical pane-mounting glue
(`core/textviewer_pane.py`), so the same explanation applies verbatim: a
Qt widget replaces the (hidden) file list in the pane's layout, and the
pane's focus proxy/Tab handling are re-pointed at it the same way.

## Implementation

- `src/main/resources/base/Plugins/Core/core/imageviewer.py`:
  - `IMAGE_EXTENSIONS` / `is_image(url)` — the extension check that routes
    "View file" to this viewer instead of the text viewer (pure, unit
    tested).
  - `load_oriented_image(path)` — reads a static image with Qt's automatic
    EXIF orientation transform.
  - `PaneImageView(QScrollArea)` — the viewer widget: a `QLabel` inside a
    `QScrollArea` (for panning when zoomed in). Loads a static image through
    `load_oriented_image` and sizes it from the loaded image, or a `.gif` via
    `QMovie` (started immediately so it animates). `keyPressEvent` mirrors
    `PaneTextView`'s: Ctrl+Shift+P opens its own palette, a zoom-shortcut match (via
    `core.textviewer_zoom.zoom_delta_for`, reused rather than duplicated)
    rescales, then a `_bindable_commands()` lookup (via
    `core.key_bindings.command_for_key_event` — see "Bindable commands"
    above, against `Viewer Key Bindings.json`) is checked before the
    hardcoded Escape/Enter/Backspace close and Tab/Backtab switch-panes
    fallbacks, so a rebind always wins; everything else (arrow keys) falls through to
    `QScrollArea`'s own panning. `resizeEvent` re-fits while in fit mode.
    A `ViewerNavigator(pane, 'image')` (from `core/viewer_navigation.py`)
    supplies the Next/Previous-file actions, the same-type toggle, and their
    bindable pseudo-commands; `_open_palette` delegates to that module's shared
    `open_viewer_palette`.
  - `_get_actions` — every row carries its command name (`image_reset_zoom`,
    `image_actual_size`, `viewer_close`, plus the navigator's), which is what
    makes Shift+Enter on it open the entry menu rather than report a nameless
    entry. Zoom in/out are built by `core/textviewer_zoom.py`'s shared
    `zoom_step`, so they name the global pane font-size commands and edit
    `Key Bindings.json` — the file whose shortcut they follow. There is no
    separate *Reset zoom* row: it ran the same `_fit_to_window` as *Fit to
    window*, and two rows cannot share one command name without their renames
    and keywords colliding.
  - `show_image_viewer(pane, url)` — mirrors `show_text_viewer`: mounts via
    `core/textviewer_pane.py`'s `begin_new_view`/`mount_view`, same as the
    text viewer.
- `src/main/resources/base/Plugins/Core/core/viewer_navigation.py` — shared by
  all three viewers: `advance(pane, direction, category)` walks the pane's own
  cursor to the next/previous viewable file (skipping non-viewable and, when the
  per-viewer "advance only for same type" toggle is on, other-category files)
  and re-runs `view_file`; `ViewerNavigator` bundles the per-viewer actions and
  commands; `open_viewer_palette` is the shared Ctrl+Shift+P handler. Same-type
  toggles persist per viewer in `Core Settings.json` (`image_viewer_advance_same_type`, etc.).
  A palette row is a `ViewerAction(title, action, hint, command_name,
  bindings_file)` — the last two optional. `command_name` is what Shift+Enter
  edits (keywords, rename, key binding); `bindings_file` overrides which Key
  Bindings file that edit writes, defaulting to `Viewer Key Bindings.json` and
  set only by the zoom rows. After an edit the palette reopens on the query
  that was typed, the way `core/commands/palette.py` does for the global one.
- `src/main/resources/base/Plugins/Core/core/imageviewer_zoom.py` — the
  viewer's scale persistence, mirroring `core/textviewer_zoom.py`'s
  font-size persistence but for a multiplicative scale factor (own settings
  key `image_viewer_zoom` in `Core Settings.json` via `core/settings.py`):
  `get_saved_scale`, `save_scale` (`None` clears → fit mode), `clamp_scale`,
  `change_image_scale` (steps by ×1.25 per zoom delta, clamped to
  0.1–10.0), `reset_image_scale`. Reuses `zoom_delta_for` from
  `core/textviewer_zoom.py` rather than duplicating the keystroke-matching
  logic.
- `src/main/resources/base/Plugins/Core/core/textviewer_pane.py` —
  `confirm_close(view)` was generalized (one line) to tolerate a view with
  no `_editing` attribute of its own, via `getattr(view, '_editing',
  False)`, so an image view (always read-only) safely reports "fine to
  close" instead of raising `AttributeError`. The only change to code
  shared with the text viewer.
- `src/main/resources/base/Plugins/Core/core/commands/opening.py` —
  `ViewFile.__call__` branches on `is_image(url)` after its existing
  exists/not-a-directory/local-file guards, calling `show_image_viewer`
  instead of `show_text_viewer` for image files; see
  [`docs/functions/view-file.md`](../functions/view-file.md).
- Tests:
  - `core/tests/test_imageviewer.py` — `is_image()`'s extension matching
    (case-insensitive, non-image rejected, no-extension rejected) and static
    image loading with EXIF rotation, normal orientation and missing files.
  - `core/tests/test_imageviewer_zoom.py` — `clamp_scale`'s bounds, and
    `change_image_scale`/`reset_image_scale`'s step/clamp/clear behaviour
    via injected `get_saved`/`save` fakes (so the math is tested without
    touching real settings I/O).
  - The remaining Qt-specific behaviour (actual paint/scaling, GIF
    animation, Tab/focus-proxy switching, the palette dialog, real
    scrollbar panning) was verified interactively, not unit-tested — same
    approach the text viewer takes (see
    [`docs/views/TEXT_VIEWER.md`](TEXT_VIEWER.md), Implementation section).
