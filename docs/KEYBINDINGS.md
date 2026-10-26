# Key bindings

Reference for fman's default keyboard shortcuts and how to add or change
your own.

## Files and load order

fman merges key bindings from several `Key Bindings.json` files, each
optional, in this order (first match for a key wins —
`Controller.handle_shortcut`,
`src/main/python/fman/impl/controller.py:35-44`):

1. `Plugins/Core/Key Bindings.json` — base bindings (all platforms).
2. `Plugins/Core/Key Bindings (Windows|Mac|Linux).json` — platform-specific
   additions/overrides, checked *before* the base file.
3. `%APPDATA%/fman/Plugins/User/Settings/Key Bindings (Windows).json`
   (Windows; equivalent per-OS `Plugins/User/Settings/` folder elsewhere) —
   **the user override file**. This is the one you edit to customize a
   running install; it takes precedence over both Core files.

A binding entry is a JSON object:

```json
{ "keys": ["Ctrl+Shift+P"], "command": "command_palette" }
```

`keys` is a one-element array holding the shortcut string (`+`-joined
modifiers); `command` is the lowercased command name. Some commands take an
extra `args` object, e.g.:

```json
{ "keys": ["Alt+F1"], "command": "show_volumes", "args": {"pane_index": 0} }
```

To add your own binding, edit (or create) your user
`Key Bindings (<OS>).json` and add an entry to the top-level array — it
doesn't need to repeat anything from the Core files, only what you're adding
or overriding.

## Editing bindings from the palette

You don't have to touch the file at all. Open the command palette
(`Ctrl+Shift+P`), find the command, press **Shift+Enter** and choose *Change
key bindings for "…"*: the shortcut list that opens adds a binding by having
you *press* it, and removes one again. Changes are live immediately — no
restart, no `reload_plugins` — and land in the same user file described above.

The screens, the conflict prompt, how a shipped default is unbound and what the
editor can't do are in
[`docs/COMMAND_PALETTE_KEYBINDINGS.md`](COMMAND_PALETTE_KEYBINDINGS.md).

The command names used here are also the keys of `Command Keywords.json`, the
file that gives a command extra, never-displayed words to find it by in the
command palette — see
[`docs/COMMAND_PALLETTE.md`](COMMAND_PALLETTE.md#hidden-search-keywords).

## Default bindings — base (all platforms)

| Keys | Command |
|------|---------|
| `Down` / `Num+Down` | `move_cursor_down` |
| `Shift+Down` | `move_cursor_down` (extends selection) |
| `Up` / `Num+Up` | `move_cursor_up` |
| `Shift+Up` | `move_cursor_up` (extends selection) |
| `Ctrl+J` | `move_cursor_down` (vim-style) |
| `Ctrl+K` | `move_cursor_up` (vim-style) |
| `Home` / `Num+Home` | `move_cursor_home` |
| `Shift+Home` | `move_cursor_home` (extends selection) |
| `End` / `Num+End` | `move_cursor_end` |
| `Shift+End` | `move_cursor_end` (extends selection) |
| `PgDown` / `Num+PgDown` | `move_cursor_page_down` |
| `Shift+PgDown` | `move_cursor_page_down` (extends selection) |
| `PgUp` / `Num+PgUp` | `move_cursor_page_up` |
| `Shift+PgUp` | `move_cursor_page_up` (extends selection) |
| `Space` | `toggle_selection` |
| `Num++` / `Num+-` | `select_group` / `deselect_group` (wildcard mask) |
| `Num+*` | `invert_selection` (files only) |
| `Ctrl+Num++` / `Ctrl+Num+-` | `select_group` (all files) / `deselect` (all) |
| `Alt+Num++` / `Alt+Num+-` | `select_same_extension` / `deselect_same_extension` |
| `Tab` | `switch_panes` |
| `Backspace` | `go_up` |
| `Enter` | `open` (navigate into folders, OS-open files) |
| `F1` | `help` |
| `F2` | `rename` |
| `F4` | `open_with_editor` |
| `Shift+F4` | `create_and_edit_file` |
| `F5` | `copy` |
| `Shift+F5` | `symlink` |
| `Shift+F6` | `rename` |
| `F6` | `move` |
| `F7` | `create_directory` |
| `F8` / `Delete` / `Num+Delete` | `move_to_trash` |
| `F9` | `open_terminal` |
| `F10` | `open_native_file_manager` |
| `F11` | `copy_paths_to_clipboard` |
| `Shift+F11` | `copy_file_name` |
| `Shift+Delete` | `delete_permanently` |
| `Alt+F1` | `show_volumes` (left pane) |
| `Alt+F2` | `show_volumes` (right pane) |
| `Num+Insert` | `move_cursor_down` (extends selection) |
| `Alt+Up` | `increase_pane_font_size` |
| `Alt+Down` | `decrease_pane_font_size` |

Keypad `+` and `-` accept `;`-separated wildcard masks; text after `|` excludes matches.
A trailing `\` (or `/`) matches folders, while `*.*` means all files.
Matching is case-insensitive and affects files only unless a folder mask is used.

Choose the program F4 starts and its arguments with **Set text editor** in the Command Center; presets are available for Notepad++, CudaText, Notepad 4, EmEditor and Ecode, or you can enter manual arguments.

`F2` (and `Shift+F6`, the dual-pane convention) edits the name in place rather than opening a dialog, and offers
*Retry* when the rename fails — see
[`docs/functions/rename.md`](functions/rename.md).

### Don't bind bare letters — they belong to the live filter

`Ctrl+J`/`Ctrl+K` are the vim-style cursor aliases deliberately: **`j` and `k`
themselves stay unbound**, and so should every other bare letter. Typing a
plain letter into a pane starts fman's live filter (the small box in the
bottom-right corner — `FilterBar`, `src/main/python/fman/impl/widgets.py:253`),
which narrows the list to matching names and jumps the cursor to the first hit.

A keypress is matched against the key bindings *before* it is offered to that
filter (`DirectoryPaneWidget._on_key_pressed`, `impl/widgets.py:216-227`), and
the binding files have no "only when the filter is closed" condition. So any
bare letter you bind is a letter you can no longer type into the filter — bind
`j` and no filename containing a `j` is reachable by typing. Put a modifier on
it and both keep working.

## Windows additions

| Keys | Command |
|------|---------|
| `Ctrl+Right` | `open_in_right_pane` |
| `Ctrl+Left` | `open_in_left_pane` |
| `Ins` | `move_cursor_down` (extends selection) |
| `Ctrl+C` | `copy_to_clipboard` |
| `Ctrl+X` | `cut` |
| `Ctrl+V` | `paste` |
| `Ctrl+Z` | `undo` |
| `Ctrl+A` | `select_all` |
| `Ctrl+D` | `deselect` |
| `Ctrl+.` | `toggle_hidden_files` |
| `Ctrl+P` | `go_to` |
| `Ctrl+Shift+P` | `command_palette` |
| `Alt+Left` | `go_back` |
| `Alt+Right` | `go_forward` |
| `Alt+F5` | `pack` |
| `Ctrl+R` | `reload` |
| `Ctrl+F1`/`F2`/`F3` | `sort_by_column` (name/size/date) |
| `Ctrl+Up` | `go_up` |
| `Alt+Enter` | `show_explorer_properties` |
| `Ctrl+\` | `go_to_root_of_current_drive` |

## macOS additions

| Keys | Command |
|------|---------|
| `Alt+Right` | `open_in_right_pane` |
| `Alt+Left` | `open_in_left_pane` |
| `Cmd+C` | `copy_to_clipboard` |
| `Cmd+X` | `cut` |
| `Cmd+V` | `paste` |
| `Cmd+Z` | `undo` |
| `Cmd+Alt+V` | `paste_cut` |
| `Cmd+A` | `select_all` |
| `Cmd+D` | `deselect` |
| `Space` | `move_cursor_down` (extends selection) |
| `Cmd+Backspace` | `move_to_trash` |
| `Cmd+.` | `toggle_hidden_files` |
| `Cmd+P` | `go_to` |
| `Cmd+Shift+P` | `command_palette` |
| `Cmd+Left` | `go_back` |
| `Cmd+Right` | `go_forward` |
| `Cmd+I` | `get_info` |
| `Cmd+F5` | `pack` |
| `Cmd+R` | `reload` |
| `Cmd+F1`/`F2`/`F3` | `sort_by_column` (name/size/date) |
| `Cmd+M` | `minimize` |
| `Cmd+Q` | `quit` |
| `Cmd+Up` | `go_up` |
| `Shift+Space` | `quick_look` |
| `Cmd+Enter` | `open_selected_files` |
| `Cmd+Ctrl+F` | `toggle_fullscreen` |

## Linux additions

| Keys | Command |
|------|---------|
| `Ctrl+Right` | `open_in_right_pane` |
| `Ctrl+Left` | `open_in_left_pane` |
| `Ins` | `move_cursor_down` (extends selection) |
| `Ctrl+C` | `copy_to_clipboard` |
| `Ctrl+X` | `cut` |
| `Ctrl+V` | `paste` |
| `Ctrl+Z` | `undo` |
| `Ctrl+A` | `select_all` |
| `Ctrl+D` | `deselect` |
| `Ctrl+.` | `toggle_hidden_files` |
| `Ctrl+P` | `go_to` |
| `Ctrl+Shift+P` | `command_palette` |
| `Ctrl+Q` | `quit` |
| `Alt+Left` | `go_back` |
| `Alt+Right` | `go_forward` |
| `Alt+F5` | `pack` |
| `Ctrl+R` | `reload` |
| `Ctrl+F1`/`F2`/`F3` | `sort_by_column` (name/size/date) |
| `Ctrl+Up` | `go_up` |

## Navigation commands without a binding

`go_to` (`Ctrl+P`) is only half of fman's navigation. `go_home` and its
siblings — `go_to_desktop`, `go_to_documents`, `go_to_downloads`,
`go_to_app_data`, `go_to_temp`, plus `go_to_local_app_data`,
`go_to_program_data`, `go_to_program_files` and `go_to_program_files_x86` on
Windows — jump straight to one well-known directory each and ship with **no
default binding**, so they are palette-only until you bind them:

```json
{ "keys": ["Alt+Home"], "command": "go_home" }
```

See [`docs/functions/go-to.md`](functions/go-to.md) for what each one resolves
to and why they exist alongside `go_to`.

`follow_shortcut` (Windows) is unbound too: on a `.lnk` file it goes to the
shortcut's destination rather than launching it. See
[`docs/functions/follow-shortcut.md`](functions/follow-shortcut.md).

## Viewer-specific bindings

The [text viewer](views/TEXT_VIEWER.md), [image viewer](views/IMAGE_VIEWER.md),
and [video viewer](views/VIDEO_VIEWER.md) each bind a handful of keys
directly — the rest fall through to text navigation/selection, image panning,
or (video) the hardcoded playback defaults below:

| Keys | Effect |
|------|--------|
| `Escape` / `Enter` / `Backspace` | Close the viewer, return to the file list |
| `Tab` / `Shift+Tab` | Switch panes (same as the file list) — view/text-edit-mode only, see below |
| `Ctrl+Shift+P` | Open the viewer's own command palette (exit/edit/save, zoom, video/mute controls) |
| Whatever `increase_pane_font_size`/`decrease_pane_font_size` are bound to (`Alt+Up`/`Alt+Down` by default) | Zoom the text/image viewer (video has no zoom) |

**Text-viewer-only defaults**, view mode (in edit mode these keys type
themselves — bind your own if you want search while editing):

| Keys | Effect |
|------|--------|
| `/` | Prompt for a search query, jump to the first match |
| `n` / `N` | Next / previous match (wraps) |
| `Escape` | Leave search mode — only while searching; otherwise it closes the viewer as usual |
| `Home` / `End` | Jump to the top / bottom of the file (`Shift+Home` etc. still select, as in Qt) |
| `PgUp` / `PgDown` | Page up / down |

**Video-only defaults** (no equivalent in the other two viewers):

| Keys | Effect |
|------|--------|
| `Space` | Play / pause |
| `Left` / `Right` | Seek −5s / +5s |
| `Up` / `Down` | Volume −5 / +5, flashing `Volume: N` on screen |

### File-list shortcuts that also work in a viewer

Commands marked `usable_in_viewer` keep their shortcuts from global
`Key Bindings.json` while a file is open. Rebinding one there also changes its
viewer shortcut. These commands appear in the viewer palette with the same
shortcut hint, and Shift+Enter edits their global binding.

| Command | Default key |
|---------|-------------|
| Copy / Move / Symlink | F5 / F6 / Shift+F5 |
| Copy paths to clipboard | F11 |
| Copy file name | Shift+F11 |
| Copy file path | Palette only (menu shows F11) |
| Edit / Terminal / Open native file manager | F4 / F9 / F10 |
| Properties | Alt+Enter (Windows) |
| Pack to archive | Alt+F5 |
| Open with… / Show only active pane / Show all panes | Palette only |

Viewer bindings, then the viewer's built-in keys, then these pane commands,
then Qt handling take precedence in that order. Other global bindings stay
out because they would change the hidden file list or take over viewer/Qt
keys. A hidden file-list selection is set aside while the command runs, so
Copy and Move act on the file on screen. If a command moves that file away,
the **Close viewer after deleting** setting controls whether the viewer closes
or shows the next file. The text viewer offers these in view mode for a real
file, but not while editing or showing content without a backing file.

### Bindable viewer commands

Every viewer action above — plus several that ship with **no** default key
(video mute/reset-volume/restart, image reset-zoom/actual-size, several text
palette actions) — is a **viewer-only pseudo-command** you can bind in your
own `Viewer Key Bindings (<OS>).json`, a **separate file** from the
`Key Bindings (<OS>).json` used for global/file-list shortcuts above. It
follows the identical base → platform → user-override merge, just under its
own filename (`core/key_bindings.py::VIEWER_KEY_BINDINGS_FILE`). These
pseudo-commands are matched by the focused viewer widget itself
(`core/key_bindings.py::command_for_key_event`, checked before that viewer's
hardcoded fallback keys — a rebind always wins) — they are **not** registered
`DirectoryPaneCommand`s and are **not** present in Core's own
`Key Bindings.json`, so putting one there instead of `Viewer Key Bindings.json`
triggers a "Command does not exist" startup alert and does nothing. These
viewer-only commands act while the matching viewer has focus; some ordinary
file-list commands also work there, as described below.

| Command | Viewer | Default key | Action |
|---------|--------|--------------|--------|
| `viewer_close` | all | Escape/Enter/Backspace | Close viewer |
| `viewer_switch_panes` | all (text: view mode only) | Tab | Switch panes |
| `viewer_open_palette` | all | Ctrl+Shift+P | Open viewer command palette |
| `viewer_next_file` / `viewer_previous_file` | all (text: view mode, backed file) | *(none)* | View next / previous file in the directory |
| `viewer_toggle_same_type_advance` | all (text: view mode, backed file) | *(none)* | Toggle "advance only for same type" (per viewer) |
| `viewer_delete_file` | all (text: view mode, backed file) | *(none)* | Move the viewed file to the trash, confirmation and all |
| `viewer_rename_file` | all (text: view mode, backed file) | *(none)* | Prompt for a new name for the viewed file |
| `viewer_toggle_close_after_delete` | all (text: view mode, backed file) | *(none)* | Toggle whether a delete closes the viewer or goes to the next file (global) |
| `video_toggle_pause` | video | Space | Play / pause |
| `video_seek_forward` / `video_seek_backward` | video | Right / Left | Seek ±5s |
| `video_volume_up` / `video_volume_down` | video | Up / Down | Volume ±5 |
| `video_mute` | video | *(none)* | Toggle mute (persists) |
| `video_reset_volume` | video | *(none)* | Volume → 100 |
| `video_restart` | video | *(none)* | Restart from 0:00 |
| `image_reset_zoom` | image | *(none)* | Fit to window |
| `image_actual_size` | image | *(none)* | Actual size (100%) |
| `text_edit` / `text_reload` | text (view mode) | *(none)* | Edit file / Reload from disk |
| `text_toggle_auto_reload` / `text_toggle_tail` | text (view mode, backed file) | *(none)* | Toggle auto-reload / tail mode |
| `text_save` / `text_save_as` / `text_revert` | text (edit mode) | *(none)* | Save / Save as… / Revert |
| `text_reset_font_size` | text (both modes) | *(none)* | Reset the viewer's own zoom (not the pane's) |
| `text_find` | text (both modes) | `/` (view mode) | Prompt for a search query, jump to the first match |
| `text_find_next` / `text_find_previous` | text (both modes) | `n` / `N` (view mode) | Next / previous match (wraps) |
| `text_search_exit` | text (both modes) | Escape (view mode, while searching) | Leave search mode |
| `text_go_to_top` / `text_go_to_bottom` | text (both modes) | `Home` / `End` (view mode) | Jump to the top / bottom of the file |
| `text_page_up` / `text_page_down` | text (both modes) | `PgUp` / `PgDown` (view mode) | Page up / down |

See each viewer's own docs
([video](views/VIDEO_VIEWER.md#bindable-commands),
[image](views/IMAGE_VIEWER.md#bindable-commands),
[text](views/TEXT_VIEWER.md#bindable-commands)) for the full per-mode list.
Example — bind **M** to mute in the video viewer, in your user
`Viewer Key Bindings (Windows).json`:

```json
{ "keys": ["M"], "command": "video_mute" }
```

Example — also bind **Ctrl+Left**/**Ctrl+Up** to close the viewer (in
addition to the Escape/Enter/Backspace defaults above):

```json
[{ "keys": ["Ctrl+Left"], "command": "viewer_close" },
 { "keys": ["Ctrl+Up"], "command": "viewer_close" }]
```

`viewer_next_file` / `viewer_previous_file` ship without a default key.
Suggested conflict-free bindings (nothing in any viewer uses them):
**Ctrl+PageDown** = next, **Ctrl+PageUp** = previous; or the mnemonic
**N** / **P** (view-mode text is read-only, so letters are free):

```json
[{ "keys": ["Ctrl+PageDown"], "command": "viewer_next_file" },
 { "keys": ["Ctrl+PageUp"], "command": "viewer_previous_file" }]
```

`view_file` (opens the internal viewer on the file under the cursor — see
[`docs/functions/view-file.md`](functions/view-file.md)) ships with **no
default binding**, precisely so it doesn't change what Enter/double-click
do. To open it with a key of your own, add it to your user
`Key Bindings (<OS>).json`, e.g. bind it to `Shift+Enter`:

```json
{ "keys": ["Shift+Enter"], "command": "view_file" }
```

Note this only opens the viewer — it doesn't replace `Enter`'s normal
behaviour (navigate into folders / OS-open files), and it will show an
alert if used on a directory or a non-local path.

`view_file_in_other_pane` is the sibling command that opens the viewer in the
**other** pane, keeping the current pane's file list visible **and focused** —
so you can keep moving the cursor through the folder and preview each file in
the other pane as you go (with only one pane open it views in place). It also
ships with **no default binding** — bind it in your user
`Key Bindings (<OS>).json`, e.g.:

```json
{ "keys": ["Ctrl+Shift+Enter"], "command": "view_file_in_other_pane" }
```

If you want the internal viewer to be your *default* action on `Enter`
instead — e.g. you view files more often than you OS-open them — bind
`Enter` to [`open_or_view`](functions/open-or-view.md) instead of
`view_file` directly. Unlike `view_file`, `open_or_view` falls back to
`open` (navigate in) when the cursor is on a directory, so folder
navigation keeps working:

```json
[{ "keys": ["Enter"], "command": "open_or_view" },
 { "keys": ["Shift+Enter"], "command": "open" }]
```

With this, `Enter` opens files in the internal viewer and still navigates
into folders; `Shift+Enter` becomes the normal OS-open action.
