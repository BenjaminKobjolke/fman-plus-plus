# Text viewer

An in-pane viewer that shows a file's contents directly inside the active
pane, replacing the file list until closed. It exists so you can peek at (or
make a quick edit to) a text file without leaving fman or waiting on an
external editor to launch. Opens read-only; a viewer-scoped command palette
can switch eligible files to editable — see [Editing](#editing) below.

## Usage

1. Put the cursor on a file and run **"View file"** from the command palette
   (or **"View file in other pane"** to open it in the opposite pane, keeping
   this pane's file list visible).
2. The file's contents fill the active pane, in place of the file list.
3. Navigate with the mouse or keyboard: arrow keys move the cursor,
   **Shift+arrow** selects text, the mouse selects too, and long lines wrap
   to the pane width. **Home**/**End** jump to the top/bottom of the file and
   **PgUp**/**PgDown** page through it (view mode; while editing, Home/End go
   to the line start/end as usual — see [Editing](#editing)).
4. Press **Escape**, **Enter**, or **Backspace** to close the viewer and
   return to the file list, with the cursor back on the same file.
5. Press **Tab** to switch to the other pane — same as the normal file list.
   The viewer stays open in this pane; pressing **Tab** again brings focus
   straight back to it. (Tab only switches panes in view mode — see
   [Editing](#editing).)
6. Press **Ctrl+Shift+P** to open the viewer's own command palette (see
   below) instead of closing with Escape/Enter/Backspace.

There's no default key binding for opening the viewer — see
[`docs/functions/view-file.md`](../functions/view-file.md) for the command
itself.

## Editing

The viewer opens read-only. Press **Ctrl+Shift+P** to open its own command
palette — a fuzzy-search picker scoped to this viewer, separate from fman's
global command palette (which can't reach the viewer anyway, since it only
searches the file-list widget and that's hidden while viewing).

**View-mode entries:** *Exit viewer*, *Edit file*, *Reload from disk*,
*Enable/Disable auto-reload*, *Enable/Disable tail mode (follow end)*,
*Increase font size*, *Decrease font size*, *Reset font size*, *Find…*,
*Find next*, *Find previous* (plus *Exit search mode* while searching — see
[Search](#search)).

**Edit-mode entries:** *Save file*, *Save file as…*,
*Revert / reload from disk*, *Enable/Disable auto-reload*,
*Enable/Disable tail mode (follow end)*, *Increase font size*,
*Decrease font size*, *Reset font size*, *Exit viewer*, *Find…*, *Find next*,
*Find previous*.

For files with a supported JSON or XML-based extension, the viewer pretty-prints
valid content automatically. In view mode, *Show original* and *Pretty print*
switch between the file as stored and its formatted display. Invalid or already
formatted content stays as it is. Reloading from disk, including auto-reload
and tail mode, applies the currently selected display mode.

Syntax colors are enabled by default for file types recognized by Pygments.
*Disable syntax colors* / *Enable syntax colors* toggles them for the current
viewer session in either mode. Files without a matching lexer remain plain text;
highlighting is skipped for text larger than 512 KiB.

Notes:

- **Entering edit mode is confirmed, not silent.** *Edit file* reports
  `Edit mode` in the [status bar](../STATUSBAR.md); the buffer looks the same
  either way. Saving reports `Saved` / `Saved as <path>` — or
  `Could not save: <reason>` if the write fails (a read-only file, a path
  whose directory doesn't exist), which leaves the buffer modified so you can
  retry with *Save file as…* rather than losing the edit.
- **Saving a pretty-printed file reformats it.** Editing uses the text shown
  in the viewer, so Save writes the indented JSON/XML display back to disk.
  To preserve the original formatting, choose *Show original* before entering
  edit mode. When entering edit mode from a pretty-printed display, the status
  bar says `Edit mode (pretty-printed - Save reformats the file)`.
- **Not every file can be edited.** *Edit file* only makes the buffer
  editable if the file wasn't [size-truncated](#behaviour) and its bytes are
  strict UTF-8 — the same replacement decoding used for display is lossy, so
  saving it back would corrupt the original file. If a file doesn't qualify,
  *Edit file* shows an alert explaining why instead of entering edit mode.
- **Tab behaves differently in edit mode.** In view mode Tab switches panes
  (see above). Once editing, Tab types a literal tab character instead —
  pane-switching would otherwise be a constant risk of the wrong keystroke
  discarding your place. Use the palette's *Exit viewer* to leave edit mode.
- **Unsaved changes are protected.** *Exit viewer* prompts
  Save / Discard / Cancel if the buffer has unsaved edits;
  *Revert / reload from disk* prompts Discard / Cancel. The same protection
  applies if you run **View file** again on a *different* file while this
  pane's viewer has unsaved edits — the new file isn't opened until you
  save, discard, or cancel.
- **Line endings.** `QPlainTextEdit` normalizes all line endings to `\n`
  internally, so saving a file that used CRLF rewrites it with LF. A known,
  accepted limitation — re-open the file in an external editor first if you
  need CRLF preserved.
- **Save file as…** prompts for a full destination path and writes there;
  the viewer then continues editing/saving that new path.

## Search

Vim-style find-in-file, view mode's keys by default:

1. Press **`/`** — a prompt opens, pre-filled with your last query. Type and
   press Enter: the first match from the cursor down is selected and scrolled
   into view.
2. The status bar then shows search mode and the keys that walk it, e.g.
   `Search: needle  (n next, N previous, Esc exit)`.
3. **`n`** goes to the next match, **`N`** to the previous one. Both wrap
   around the ends of the file, appending `(wrapped)` to the status line when
   they do. A query the file doesn't contain shows `No match: …` and leaves
   the cursor where it was.
4. **`Esc`** leaves search mode and clears the status line. Only then does a
   second `Esc` close the viewer — searching never costs you your place by
   accident.

Notes:

- **Matching is case-insensitive**, literal (no regex), and only the current
  match is highlighted — there is no highlight-all pass over the file.
- **Every step is also a palette entry:** *Find…*, *Find next*,
  *Find previous*, and — only while search mode is on — *Exit search mode*.
  Each shows its key as a hint, following your own binding if you rebound it
  (see [Bindable commands](#bindable-commands)).
- **Edit mode has no default keys**, since `/`, `n` and `N` have to type
  themselves there. Search from the palette instead, or bind a key of your own
  (e.g. `Ctrl+F` → `text_find`), which works in both modes. Entering edit mode
  leaves search mode, so the status bar stops advertising keys that now type.
- The status line is invisible while the [status bar](../STATUSBAR.md) is
  toggled off; search itself still works.

## Reload and auto-reload

- **Reload keeps your place.** *Reload from disk* (view mode) and
  *Revert / reload from disk* (edit mode) preserve the viewport's scroll
  position and cursor location rather than jumping back to the top of the
  file. Both report `Reloaded from disk` in the
  [status bar](../STATUSBAR.md) — a file that hasn't changed on disk reloads
  to a pane that looks identical, so without the message there is nothing to
  tell you it ran.
- **A file that stops being editable says so.** If a reload finds the file
  now too large or no longer valid UTF-8, the viewer drops back to read-only
  and reports `File no longer editable - now read-only` instead of the plain
  reload confirmation.
- **Auto-reload** is an opt-in, per-view toggle (*Enable/Disable auto-reload*
  in the palette): once enabled, the viewer watches the open file on disk and
  reloads automatically whenever it changes, still preserving scroll
  position. It's session-only — every newly opened file starts with
  auto-reload off, and closing the viewer forgets the setting.
- **Tail mode** (*Enable/Disable tail mode (follow end)*) is the log-following
  variant of auto-reload: instead of preserving scroll position, each reload
  jumps to the end of the file, like `tail -f`. Switching between plain
  auto-reload and tail mode doesn't require turning auto-reload off first.
- **Unsaved edits are never overwritten.** If the file changes on disk while
  editing with unsaved changes, auto-reload/tail mode skips the reload and
  shows a status message (`File changed on disk (not reloaded)`) instead of
  discarding your edits.

## Zoom

The viewer has its own font-size zoom, independent of the file-list panes'
zoom ([pane font size](../functions/pane-font-size.md)):

1. Whatever key(s) you have **Increase font size** / **Decrease font size**
   bound to (`Alt+Up` / `Alt+Down` by default, from `Key Bindings.json`) also
   zoom the viewer's text — no separate binding to learn. This works in the
   viewer whether or not it's in edit mode, and doesn't interfere with typing.
2. The same **Increase font size** / **Decrease font size** actions are also
   in the viewer's own command palette (Ctrl+Shift+P), each showing its
   current shortcut as a hint, plus a palette-only **Reset font size**.
3. The chosen size is remembered separately from the pane list's own zoom —
   survives closing/reopening the viewer and restarting fman — until reset.
4. Each step reports the size it settled on in the
   [status bar](../STATUSBAR.md) (`Font size 12`, or `Font size reset`), from
   the key path as well as the palette — the clamp at 6pt/40pt is otherwise
   indistinguishable from a keystroke that didn't register.

Rebinding `increase_pane_font_size`/`decrease_pane_font_size` in
`Key Bindings.json` changes what the viewer listens for too, since it looks
up the *current* binding rather than hardcoding `Alt+Up`/`Alt+Down`. That is
also why **Shift+Enter** on those two palette rows edits
`Key Bindings (<OS>).json` and not the viewer file — see
[Changing key bindings from the palette](../COMMAND_PALETTE_KEYBINDINGS.md).
*Reset font size* is the viewer's own (`text_reset_font_size`), so it edits
the viewer file like every other row here.

## Bindable commands

In view mode for a file, suitable file-list shortcuts such as F5 (Copy) also
work; see [shared viewer shortcuts](../KEYBINDINGS.md#file-list-shortcuts-that-also-work-in-a-viewer).

Beyond zoom (already bindable via the pane font-size shortcut, above, and
still read from `Key Bindings (<OS>).json`), the palette actions are
viewer-only pseudo-commands you can bind your own key to in your own
`Viewer Key Bindings (<OS>).json` — a **separate file**, see
[`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings). A
rebind always wins over the default key listed below; the set differs by
mode (see [Editing](#editing)).

| Command                     | Default key             | Mode | Action                  |
|-------------------------------|--------------------------|------|--------------------------|
| `text_edit`                   | *(none — palette only)*  | view | Edit file                |
| `text_reload`                 | *(none — palette only)*  | view | Reload from disk         |
| `text_toggle_auto_reload`     | *(none — palette only)*  | view, with a backing file | Enable/disable auto-reload |
| `text_toggle_tail`            | *(none — palette only)*  | view, with a backing file | Enable/disable tail mode |
| `text_save`                   | *(none — palette only)*  | edit | Save file                |
| `text_save_as`                | *(none — palette only)*  | edit | Save file as…            |
| `text_revert`                 | *(none — palette only)*  | edit | Revert / reload from disk |
| `text_toggle_pretty`          | *(none — palette only)*  | view | Switch between pretty-printed and original JSON/XML text |
| `text_toggle_syntax_colors`   | *(none — palette only)*  | both | Toggle Pygments syntax colors for this viewer session |
| `text_find`                   | `/` (view mode)          | both | Prompt for a search query, jump to the first match |
| `text_find_next`              | `n` (view mode)          | both | Next match (wraps)      |
| `text_find_previous`          | `N` (view mode)          | both | Previous match (wraps)  |
| `text_go_to_top`              | `Home` (view mode)       | both | Jump to the top of the file |
| `text_go_to_bottom`           | `End` (view mode)        | both | Jump to the bottom of the file |
| `text_page_up`                | `PgUp` (view mode)       | both | Page up                 |
| `text_page_down`              | `PgDown` (view mode)     | both | Page down               |
| `text_reset_font_size`        | *(none — palette only)*  | both | Reset the viewer's own zoom (leaves the pane's alone) |
| `text_search_exit`            | Escape (view mode, while searching) | both | Leave search mode |
| `viewer_close`                | Escape/Enter/Backspace   | both | Close viewer (edit mode: with unsaved-changes prompt) |
| `viewer_switch_panes`         | Tab                      | view only | Switch panes — deliberately not bindable in edit mode, where Tab always types |
| `viewer_open_palette`         | Ctrl+Shift+P             | both | Open viewer command palette |
| `viewer_next_file` / `viewer_previous_file` | *(none — palette only)* | view, with a backing file | View next / previous file in the directory |
| `viewer_toggle_same_type_advance` | *(none — palette only)* | view, with a backing file | Toggle "advance only for same type" |
| `viewer_delete_file` | *(none — palette only)* | view, with a backing file | Move the file to the trash |
| `viewer_rename_file` | *(none — palette only)* | view, with a backing file | Rename the file, keeping it open |
| `viewer_toggle_close_after_delete` | *(none — palette only)* | view, with a backing file | Toggle whether a delete closes the viewer or goes to the next file |

Next/previous and the same-type toggle are **shared** across all three viewers
(view mode only here — never while editing, and not in the backing-file-less
release-notes view) — see
[File viewers](../viewers/FILE_VIEWERS.md#shared-behaviour) for how they behave
and [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md#viewer-specific-bindings) for
suggested keys.

## Behaviour

- **Read-only by default.** Content can always be navigated and selected
  (e.g. to copy); becomes writable only after *Edit file* — see
  [Editing](#editing).
- **Word-wrapped.** Lines wrap at the pane's width rather than requiring
  horizontal scrolling.
- **Size-capped.** At most 2 MB of a file is read; larger files are
  truncated with a trailing notice, so opening a huge or binary-ish file
  can't freeze the UI.
- **Encoding-safe.** Content is decoded as UTF-8 with invalid bytes replaced
  (`�`) rather than guessing an encoding or raising on non-UTF-8 files.
- **Per-pane, one at a time.** Viewing a new file while one is already open
  in that pane replaces it; the other pane is unaffected.
- **Plain text only.** `.md` is shown as raw text, not rendered.
- **Follows the active theme.** Background/foreground match the file list's
  actual palette colors, not a hardcoded value — see
  [`docs/THEMES.md`](../THEMES.md).

## Why it works while the file list is hidden

fman's keyboard shortcuts are not global — they only fire for the file list
widget specifically (`FileListView.key_press_event_filter` →
`Controller.handle_shortcut`). The viewer is a separate Qt widget
(`QPlainTextEdit`) added to the same pane's layout, with the file list
hidden underneath it. Once it has keyboard focus, arrow keys reach it
directly instead of moving the (hidden) file cursor.

The same applies to **Tab**: it's normally bound to `switch_panes`
(`Key Bindings.json`) and only reaches that binding because
`FileListView.key_press_event_filter` forwards it — a hidden file list can't
receive key events at all. The viewer's `keyPressEvent` explicitly
intercepts `Tab`/`Shift+Tab` and calls `switch_panes` itself
(`pane.run_command('switch_panes')`) so the pane's own Tab binding still
works while the file list underneath is hidden. `show_text_viewer` also
re-points the pane widget's Qt focus proxy at the viewer
(`widget.setFocusProxy(view)`, normally the file list, see
`DirectoryPaneWidget.__init__`), so `switch_panes` tabbing back into this
pane focuses the viewer again instead of the hidden file list.

## Two Qt quirks this had to work around

Both were only found by testing real keyboard interaction, not by reading
Qt's docs — worth knowing if this code needs touching again:

- **`setReadOnly(True)` disables *all* keyboard cursor movement, not just
  editing.** In this Qt build, a read-only `QPlainTextEdit` silently ignores
  Right/Left/Shift+Right/etc. — the cursor never moves and nothing gets
  selected, even though the widget reports having focus. Fixed by calling
  `setTextInteractionFlags(Qt.TextSelectableByKeyboard |
  Qt.TextSelectableByMouse)` right after `setReadOnly(True)`, which restores
  keyboard navigation and selection while keeping the widget non-editable.
- **The app-wide theme silently hides the blinking caret.** `Theme.css`'s
  `* { font-size: ...pt; }` wildcard rule (applied via
  `QApplication.setStyleSheet`) touches every widget, including this one.
  Once *any* stylesheet touches a widget, Qt switches it from
  palette-based rendering to the QSS style engine — which only draws the
  blinking caret if `color`/`background-color` are set explicitly in that
  widget's own stylesheet. This is the same wildcard-rule problem
  [pane font size](../functions/pane-font-size.md) already works around for
  the file list (`FileListView { font-size: ...pt; }` beats the app-wide
  `*` rule). Fixed the same way: the viewer sets its own
  `QPlainTextEdit { color: ...; background-color: ...; }` — but with colors
  read live from the file view's own `QPalette` (`Base`/`Text`) rather than
  a hardcoded value, so the caret renders *and* matches whatever theme is
  active, including a custom `Theme.css`/palette. See
  [`docs/THEMES.md`](../THEMES.md) for how fman themes actually work.

## Implementation

The feature is split across a few small modules, partly to stay under the
project's 300-line-per-file cap and partly because the split lines up with
genuinely separate concerns (reading a file vs. the Qt widget vs. zoom):

- `src/main/resources/base/Plugins/Core/core/textviewer_io.py` — pure (no Qt)
  file-reading helpers, factored out so they're usable/testable independent
  of the widget:
  - `read_capped(path)` → `(data, truncated)`, the capped byte read.
  - `decode_for_display(data, truncated)` — UTF-8-with-replace decode plus
    the truncation notice.
  - `is_editable(data, truncated)` — `False` if the read was truncated or the
    bytes aren't strict UTF-8, else `True`. Drives whether *Edit file* is
    allowed (see [Editing](#editing)).
  - `load_for_view(path)` → `(display_text, editable)` — the full pipeline
    (the three above, chained), used by both the initial open
    (`show_text_viewer`) and *Revert* so neither repeats the sequence.
  - `read_text_for_view(path)` — `load_for_view` minus the editability half;
    a plain "read this file for display" helper.
- `src/main/resources/base/Plugins/Core/core/settings.py` —
  `get_setting(json_name, key)` / `save_setting(json_name, key, value)`, the
  generic "one key in a JSON settings file, `None` clears it" pattern.
  Extracted after it turned out to be duplicated verbatim (just a different
  key) between the pane font-size feature's own settings functions
  (`core/commands/pane_view.py`) and this feature's
  (`core/textviewer_zoom.py`, below).
- `src/main/resources/base/Plugins/Core/core/font_size.py` — `clamp_font_size`
  and the min/max bounds, shared verbatim by both this feature and
  [pane font size](../functions/pane-font-size.md) so the two zoom features
  step/clamp identically. Split into its own module (rather than one
  importing the other) because the Core command package imports
  `core/textviewer.py` at load time, via `core/commands/opening.py` — the
  reverse import would be circular.
- `src/main/resources/base/Plugins/Core/core/key_bindings.py` —
  `get_shortcuts_for_command(key_bindings, command)` (which shortcut(s) the
  user currently has a command bound to, in the merged
  `Key Bindings.json`) and `format_shortcut_hint(shortcuts)` (join +
  Mac-symbol substitution for display). Also shared with — and, after this
  feature, factored out of — `core/commands/palette.py`'s `CommandPalette`,
  which uses the same two functions for its own hint display. Same
  circular-import reason as `font_size.py`. `command_for_key_event(key_event,
  key_bindings, command_names)` generalizes `zoom_delta_for` below (a single
  hardcoded command pair) to an arbitrary set of viewer-only pseudo-commands:
  first name in `command_names` whose shortcut matches, else `None`.
  `dispatch_bindable_command(key_event, key_bindings, commands)` wraps it —
  looks up and immediately calls the matched command, returning whether one
  fired — so each viewer's `keyPressEvent` does one
  `if dispatch_bindable_command(...): return` instead of repeating the
  lookup-then-call sequence. Shared by all three viewers'
  `_bindable_commands()` lookups (see "Bindable commands" above, and the
  image/video viewer docs for their own lists).
- `src/main/resources/base/Plugins/Core/core/textviewer_zoom.py` — the
  viewer's own zoom, independent of pane font size (own settings key
  `text_viewer_font_size` in `Core Settings.json` via `core/settings.py`, own
  base-size fallback): `get_saved_view_font_size`, `save_view_font_size`,
  `effective_view_font_size` (reads the live widget's `QFontInfo` as the
  step-from base when nothing's saved yet — same technique
  `core/commands/pane_view.py`'s `_effective_font_size` uses for the file
  list), `change_view_font_size`, `reset_view_font_size` (these two take an
  `apply_size(size_or_None)` callback rather than touching a stylesheet
  directly, keeping this module PyQt-styling-agnostic), and
  `zoom_delta_for(key_event, key_bindings)` — the pure keystroke-matching
  function: builds a `QtKeyEvent` (`fman.impl.util.qt.key_event`, the same
  class `Controller.handle_shortcut` uses) from the raw Qt event and checks
  it against `get_shortcuts_for_command`'s result for
  `increase_pane_font_size`/`decrease_pane_font_size`, so it always follows
  the user's actual configured shortcut rather than a hardcoded
  `Alt+Up`/`Alt+Down` (the two command names live here as
  `INCREASE_COMMAND`/`DECREASE_COMMAND`, imported by the image viewer too, so
  the strings aren't re-typed per module).
  `zoom_step(title, command, key_bindings, run)` builds one step entry — label,
  shortcut hint, command name, and `KEY_BINDINGS_FILE` as the entry's bindings
  file, since a Shift+Enter rebind of a step has to land in the global file
  `zoom_delta_for` actually reads. Shared with the image viewer's Zoom in/out,
  which steps a scale rather than a font size but hints and rebinds
  identically. `RESET_COMMAND` (`text_reset_font_size`) is the viewer-only
  pseudo-command *Reset font size* ships, registered in
  `PaneTextView._bindable_commands()` for both modes at once (it is the one
  zoom action with no global counterpart — `reset_pane_font_size` resets the
  file list's zoom, not this one).
  `zoom_actions(view, apply_size, key_bindings)` builds
  the three zoom palette entries (labels + shortcut hints) here rather than in
  `core/textviewer.py`, which the search feature pushed up against the
  300-line cap.
- `src/main/resources/base/Plugins/Core/core/textviewer_pane.py` — pane-
  mounting glue shared by `show_text_viewer`/`show_text_in_viewer`, split out
  of `core/textviewer.py` to stay under the project's 300-line file cap:
  - `caret_fix_css(bg, fg, font_size=None)` — pure helper building the
    caret-fix stylesheet rule from the given colors, with the zoom override
    folded into the same local rule when given.
  - `confirm_close(view)` — shared save/discard/cancel prompt for a mid-edit,
    unsaved view. Returns whether it's safe to close/replace it. Used by
    `PaneTextView._exit_with_dirty_check` *and* by `begin_new_view` before it
    replaces the pane's currently open view, so running **View file** again
    on a different file (or opening Release Notes) can't silently discard
    unsaved edits in the one already open.
  - `begin_new_view(pane)` / `mount_view(pane, widget, view, focus_view=True)`
    — the shared "replace whatever's currently mounted, then swap the new
    `PaneTextView` into the pane's layout" sequence (confirm-close, read live
    palette colors, hide the file list, re-point the focus proxy, deferred
    `setFocus`), used by both `show_text_viewer` and `show_text_in_viewer`.
    `focus_view=False` mounts the viewer without grabbing focus and instead
    re-focuses the *opposite* pane — used when viewing into the other pane
    (`view_file_in_other_pane`, see
    [`docs/functions/view-file.md`](../functions/view-file.md)) so browsing
    stays in the pane the command ran from.
  - `close_view(pane_widget)` — unmounts the current viewer and restores the
    file list; re-exported from `core/textviewer.py` as `close_text_viewer`
    for API stability.
- `src/main/resources/base/Plugins/Core/core/textviewer_reload.py` — the
  scroll/cursor-preserving reload shared by manual *Reload*/*Revert* and
  auto-reload, split out of `core/textviewer.py` to stay under the 300-line
  cap. Like `confirm_close` above, its functions operate directly on the
  `PaneTextView` instance (`view`) passed in rather than staying fully
  decoupled:
  - `set_text_preserving_scroll(view, text)` — saves the scrollbar value and
    cursor position, calls `setPlainText`, then restores both (clamped to the
    new text's length, in case the file shrank) — restoring *after*
    `setPlainText` because that call resets the scroll range.
  - `scroll_to_end(view)` — moves the cursor to the end and the scrollbar to
    its maximum; the tail-mode counterpart to the above.
  - `reload_from_disk(view, tail)` — the shared pipeline: `load_for_view`,
    update `_editable`, apply either `set_text_preserving_scroll` or (when
    `tail`) `setPlainText` + `scroll_to_end`, and fall back to read-only via
    `view._set_read_only()` if the reloaded file is no longer editable. Used
    by `PaneTextView._revert` and by `core/textviewer_watch.py`'s
    `on_file_changed`, so the load+editability+modified-state sequence is
    specified once. Returns whether it fell back to read-only, so `_revert`
    reports `Reloaded from disk` only when that more important message
    (`File no longer editable - now read-only`) isn't the one to show.
- `src/main/resources/base/Plugins/Core/core/textviewer_save.py` — the write
  direction, the same shape as `textviewer_reload.py` above (operates on the
  `view` passed in; split out for the 300-line cap):
  - `write_view(view, path)` — encodes the buffer as UTF-8 and writes it,
    returning `False` after reporting `Could not save: <reason>` if the write
    raises `OSError`. A palette action must not traceback, and must not leave
    the user believing a failed save happened.
  - `save(view)` / `save_as(view)` — the two palette entries; both go through
    one `_persist`, so notify + clear-modified + report can't drift apart.
- `src/main/resources/base/Plugins/Core/core/textviewer_search.py` — the
  [search](#search) feature, injected into `PaneTextView` as a `ViewerSearch`
  collaborator the same way `ViewerNavigator` is (see
  `core/viewer_navigation.py`), so the widget gains four palette entries and
  four bindable commands without growing past the 300-line cap:
  - `find_index(text, query, from_pos, backward=False)` — the pure matcher:
    `(index, wrapped)` or `None`, case-insensitive, wrapping once at either
    end. The second (wrapped) scan only runs when the first came up empty, so
    a normal hit never re-scans the buffer.
  - `key_hint(key_bindings, command, default)` / `search_status(query, hints)`
    — the palette hint and the status-bar line, both following the user's own
    `Viewer Key Bindings.json` and falling back to `/`, `n`, `N`, `Esc`. Built
    on `core/key_bindings.py`'s `get_shortcuts_for_command` /
    `format_shortcut_hint`, like the zoom entries' hints.
  - `ViewerSearch.handle_key(event)` — the hardcoded view-mode keys, called
    from `keyPressEvent` *before* the Escape/Enter/Backspace close block so
    Escape leaves search mode before it closes the viewer, and returning
    `False` when search mode is off so that fallthrough still happens.
  - `core/tests/test_textviewer_search.py` covers the three pure functions
    (including both wrap directions and a rebound hint); the Qt half
    (selection, scrolling, the modal prompt) is verified interactively, like
    the rest of the viewer's Qt behaviour.
- `src/main/resources/base/Plugins/Core/core/textviewer_cursor.py` — the
  Home/End/PgUp/PgDown cursor keys, injected as a `ViewerCursor` collaborator
  with the same `handle_key`/`actions`/`commands` shape as `ViewerSearch`
  above, and reusing its `key_hint` for the palette hints:
  - `COMMANDS` — one row per pseudo-command (name, hardcoded default key,
    palette title, what it does to the view), so the palette order, the
    defaults and the bindable dict all come from a single table.
  - `ViewerCursor.handle_key(key_event)` — the view-mode defaults, called from
    `keyPressEvent` after the viewer-bindings dispatch (a rebind wins) and
    after search. Takes the `QtKeyEvent` that method already built, so
    matching is `QKeySequence` exact-match and `Shift+Home`, `Ctrl+Home` and
    `Num+Home` keep falling through to Qt's own handling.
  - Top uses `moveCursor(QTextCursor.Start)` and bottom reuses
    `scroll_to_end` from `core/textviewer_reload.py`. Paging hands a
    synthesized `PgUp`/`PgDown` event to `QPlainTextEdit.keyPressEvent`:
    `QTextCursor` has no page-move operation, so Qt's own paging is only
    reachable through that method.
  - `core/tests/test_textviewer_cursor.py` covers all of it against a fake
    view (no `QApplication`), including the modified-key fallthrough and the
    rebound hint.
- `src/main/resources/base/Plugins/Core/core/textviewer_watch.py` — auto-reload
  and tail mode, also split out to stay under the 300-line cap:
  - `start_watch(path, on_changed, parent)` — wraps `QFileSystemWatcher`,
    parented to `parent` (the viewer widget) so it's destroyed automatically
    when the widget is, with no separate teardown path. Re-adds `path` to the
    watch list on every change, since many editors save via atomic rename
    (write a temp file, rename over the original), which silently drops Qt's
    watch on the original path.
  - `toggle_auto_reload(view)` / `toggle_tail(view)` — the two palette
    actions; each starts/stops watching depending on whether that specific
    mode (plain vs. tail) is already active, so switching from one to the
    other doesn't require turning auto-reload off first.
  - `start_auto_reload(view, tail)` / `stop_auto_reload(view)` — the shared
    start/stop logic behind both toggles, plus a status message
    (`Auto-reload on`/`Tail mode on`/`Auto-reload off`).
  - `on_file_changed(view)` — the `QFileSystemWatcher.fileChanged` handler:
    skips the reload with a status message
    (`File changed on disk (not reloaded)`) if `view` is mid-edit with
    unsaved changes, skips silently if the path doesn't exist yet (transient
    during an atomic save), otherwise calls `reload_from_disk`.
- `src/main/resources/base/Plugins/Core/core/textviewer.py`:
  - `PaneTextView(QPlainTextEdit)` — the viewer/editor widget. Tracks
    `_editable` (can this file be edited at all) and `_editing` (is it
    currently in edit mode) separately, plus `_watcher` (the active
    `QFileSystemWatcher`, or `None` when auto-reload is off) and `_tail`
    (plain auto-reload vs. tail mode) — both reset per view, so a newly
    opened file always starts with auto-reload off. `keyPressEvent`:
    - `Ctrl+Shift+P` always opens the viewer-scoped palette: `_open_palette`
      hands `_get_actions` to the shared `open_viewer_palette` in
      `core.viewer_navigation`, built on the same
      `show_quicksearch`/`QuicksearchItem` API as fman's global command palette
      and filtered with `core.quicksearch_matchers.contains_chars`. That helper
      (and the per-viewer `ViewerNavigator`) is shared by all three viewers, so
      the palette plumbing lives in one place instead of being copied into each.
    - A zoom-shortcut match (via `zoom_delta_for`) is checked next, before
      the edit-mode passthrough, so it zooms rather than getting typed into
      the buffer.
    - A `_bindable_commands()` lookup (via
      `core.key_bindings.command_for_key_event`, against
      `Viewer Key Bindings.json` — see "Bindable commands" above) is checked
      next, same reasoning: before the edit-mode
      passthrough, so e.g. a user-bound `Ctrl+S`→`text_save` fires instead of
      typing an `S`. `_bindable_commands()` mirrors `_get_actions`'s
      view/edit split so a bound key always does what its palette entry
      does; `viewer_switch_panes` is only present in the view-mode dict.
    - While `_editing`, everything else (including Tab) is forwarded to
      `QPlainTextEdit`'s native handling — Exit/Save/Revert become
      palette-only (or user-bound) so a stray keystroke can't lose focus or
      discard edits.
    - Otherwise (view mode), Escape/Enter/Return/Backspace close and
      Tab/Shift+Tab switch panes, as before.
    - Action methods: `_enter_edit_mode`, `_write` (shared by `_save`/
      `_save_as`), `_save`, `_save_as`, `_revert` (delegates the actual
      reload to `core.textviewer_reload.reload_from_disk`, keeping only the
      unsaved-changes confirmation here), `_exit_with_dirty_check`,
      `_apply_font_size` (the `apply_size` callback passed to
      `change_view_font_size`/`reset_view_font_size`), `_set_read_only`
      (the `setReadOnly(True)` + interaction-flags pair from the Qt quirk
      below, shared by `__init__` and by `reload_from_disk` falling back to
      read-only when a reload turns out non-editable). Dirty-checking reads
      `self.document().isModified()`, which `setPlainText`/
      `setModified(False)` reset naturally. `_get_actions` builds the
      auto-reload/tail palette entries' labels from `_watcher`/`_tail` and
      wires them to `core.textviewer_watch.toggle_auto_reload`/
      `toggle_tail`, only when `_path` is set (`show_text_in_viewer`'s
      Release Notes view has no backing file to watch).
  - `show_text_viewer(pane, url)` / `show_text_in_viewer(pane, text)` /
    `close_text_viewer(pane_widget)` — mount/unmount the viewer in the
    pane's own `QVBoxLayout` (`pane._widget.layout()`). `show_text_viewer`
    reads `url` from disk (this command, [View file](../functions/view-file.md));
    `show_text_in_viewer` shows arbitrary text with no backing file and is
    always read-only — used by the
    [Release Notes](RELEASE_NOTES.md) command to render a release's notes
    without writing a temp file. Both are `@run_in_main_thread`, since
    fman commands run on a background thread, and both delegate the actual
    mounting to `core/textviewer_pane.py`'s `begin_new_view`/`mount_view`
    (confirm-close, palette colors, layout swap, focus proxy) — split out of
    this module to stay under the project's 300-line file cap. Focus is
    grabbed via a deferred `QTimer.singleShot(0, view.setFocus)` rather than
    immediately, since the command palette's modal dialog restores focus to
    the (now hidden) file view as it closes, right before this code runs —
    grabbing focus synchronously would get clobbered by that restore.
- `src/main/resources/base/Plugins/Core/core/commands/opening.py` —
  `ViewFile` (`DirectoryPaneCommand`), the palette command that triggers this;
  see [`docs/functions/view-file.md`](../functions/view-file.md). `core/commands/pane_view.py` is where
  `increase_pane_font_size`/`decrease_pane_font_size`/`reset_pane_font_size`
  live (pane font-size zoom, reused by `core/textviewer_zoom.py` as above).
- Tests, split the same way as the production modules:
  - `core/tests/test_textviewer_io.py` — `read_text_for_view`/`read_capped`'s
    byte cap and truncation notice, `is_editable`'s truncation/encoding
    rules, and `load_for_view`'s combined text+editability result.
  - `core/tests/test_textviewer_zoom.py` — `zoom_delta_for`'s shortcut
    matching, including that it follows a rebind rather than only the
    default `Alt+Up`/`Alt+Down`.
  - `core/tests/test_key_bindings.py` — `command_for_key_event`'s matching,
    order-independence across `command_names`, and no-match case; shared by
    all three viewers.
  - `core/tests/test_textviewer_pane.py` — `caret_fix_css`'s color/font-size
    substitution and selector.
  - The remaining Qt-specific behaviour (interaction flags, actual caret
    paint, Tab/focus-proxy switching, the palette dialog itself,
    save/revert/exit prompts, the actual zoom application) was verified
    interactively and with a headless `QTest.keyClick` script rather than an
    automated test, since it depends on real focus/paint/modal behaviour
    that unit tests don't exercise well.
