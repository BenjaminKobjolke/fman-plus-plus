# Rename

Renames the file or folder under the cursor by editing its name inline in
the file list — no dialog. A failed rename offers **Retry**, so the name
you typed is never thrown away just because another program had the file
open.

For moving a file somewhere else, or renaming *and* moving in one step,
use [`move`](../KEYBINDINGS.md) (`F6`) — `rename` deliberately refuses
paths.

## Usage

1. Put the cursor on a file or folder.
2. Press `F2` or `Shift+F6` (or run **Rename** from the command palette, or pick
   **Rename** from the file context menu).
3. The name becomes an editable field in place, with part of it
   preselected — see *Notes*.
4. Type the new name and press `Enter`. `Esc` cancels.

After a successful rename the cursor follows the item to its new name.

## Commands

| Command name | Palette label | Default key binding | Shown when                 |
|--------------|---------------|---------------------|----------------------------|
| `rename`     | Rename        | `F2`, `Shift+F6`    | something is under cursor  |

Also in the right-click menu of any item, file or folder — `File Context
Menu (<OS>).json`, captioned `Rena&me` on Windows and Linux. It is
deliberately absent from `Folder Context Menu (<OS>).json`, which is the
menu for empty space in the pane (no item under the mouse), where there
is nothing to rename.

## Notes

- **What is preselected.** For a file, everything up to the extension, so
  typing replaces the base name and keeps `.txt`. Double extensions
  `.tar.gz`, `.tar.xz` and `.pkg.tar.xz` count as one extension. For a
  folder, the whole name is selected — folders have no extension to
  protect.
- **Case-only renames work.** `Foo` → `foo` is not treated as "already
  exists", even on a case-insensitive filesystem.
- **No paths.** A new name containing a path separator (or `..`/`.`) is
  refused with *"Relative paths are not supported. Please use Move (F6)
  instead."* On Windows both `\` and `/` count.
- **Existing target.** Renaming onto a name that already exists is
  refused with *"`<name>` already exists!"* — rename never silently
  overwrites. (`move` is the command that asks about overwriting.)
- **Empty or unchanged name** does nothing at all, silently.
- **Retry on failure.** If the rename fails, the alert offers
  **Retry** (default, so `Enter` retries) and **Cancel**:

  ```
  Access was denied trying to rename pdf-to-jpg to _old_pdf-to-jpg.
                      [ Retry ]  [ Cancel ]
  ```

  Retry re-attempts the *same* rename with the *same* target name. The
  usual cause is another program holding the file or folder open — an
  editor, a terminal sitting in that directory, a git GUI. Close it,
  press `Enter`, done. Cancel and `Esc` both give up.

  A `PermissionError` produces the "Access was denied" wording above; any
  other failure says *"Could not rename X to Y."* Both offer Retry.

- **Protected folders.** In a folder that needs administrator rights
  (`C:\Program Files\…`) the rename raises a UAC prompt instead — Retry
  could never succeed there. See [elevation](elevation.md).

- **Usually instant.** The new name always lands in the same directory,
  so on a local filesystem this is a single `os.rename` and the progress
  dialog never gets a chance to appear. Inside an archive
  (`zip://…`) it is real work — 7-Zip rewrites the archive, with progress
  and a working Cancel. See [`docs/ARCHIVES.md`](../ARCHIVES.md).

## Implementation

Three pieces, all in
`src/main/resources/base/Plugins/Core/core/commands/rename.py`:

- `Rename` (`DirectoryPaneCommand`) — only opens the editor. Passes
  `_on_name_edited` as the `pane.edit_name(...)` callback, and calls
  `is_dir` to decide how much of the name to preselect (via
  `_find_extension_start`, imported from `core/commands/editor.py`,
  which `create_and_edit_file` shares), then
- `RenameListener` (`DirectoryPaneListener`) — keeps the legacy path for
  callers that use `pane.edit_name(...)` without a callback. Both it and the
  callback use `_on_name_edited`, which does the validation above (empty/unchanged, relative path,
  existing target via `exists` + `samefile`), then hands off to
  `submit_task(_Rename(...))`.
- `_Rename` (`Task`) — performs the move. Its body is a retry loop:
  `prepare_move(...)` is re-run on every attempt because the subtasks it
  yields are single-use, and `set_progress(0)` resets the bar so a retry
  does not start visually full. The alert is
  `self.show_alert(message, RETRY | CANCEL, RETRY)`; `Esc` returns `0`,
  which is falsy against `& RETRY` and so cancels.

`RETRY` is fman's own re-export of `QMessageBox.Retry`, added in
`src/main/python/fman/__init__.py` alongside `OK`, `CANCEL`, `YES`, … and
listed in `__all__`, so plugins get it from `from fman import *`.

Tests: `RenameTest` in
`src/main/resources/base/Plugins/Core/core/tests/commands/test_rename.py`
covers retry (the move is re-run, cursor lands on the destination) and
both ways of giving up (Cancel, and `Esc`'s `0`).
