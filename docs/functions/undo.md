# Undo file operations

Use **Undo** to reverse the most recent supported file operation. Undo history
lasts only while fman is open and is cleared when fman exits. Each press undoes
one operation, starting with the most recent.

## Usage

Press `Ctrl+Z` on Windows or Linux, or `Cmd+Z` on macOS. You can also find
**Undo** in the command palette (`Ctrl+Shift+P`).

Undo supports moving files to the trash, moving files between folders,
renaming files and copying files. Undoing a copy asks before moving the copies
to the trash. Undo skips files when their original location is occupied by a
different file, and reports any failures.

Restoring files from the trash is supported on Windows. On macOS and Linux,
Undo reports that trash restoration is unsupported; other supported operation
types can still be undone there. If there is no operation to undo, fman says
"Nothing to undo."

Undo is not recorded as a new operation. Ctrl+Z or Cmd+Z in the in-pane text
editor continues to undo text edits.

## Commands

| Command name | Palette label | Keywords | Default key binding |
|--------------|---------------|----------|---------------------|
| `undo` | Undo | undo, undelete, restore deleted files, put back | `Ctrl+Z` (Windows/Linux), `Cmd+Z` (macOS) |

The words listed under *Keywords* are hidden search terms. See
[the command palette](../COMMAND_PALLETTE.md#hidden-search-keywords).

## Implementation

- `src/main/resources/base/Plugins/Core/core/commands/undo.py` — applies the
  newest saved operation and reports failures.
- `src/main/resources/base/Plugins/Core/core/undo_history.py` — keeps the
  session-only operation history.
- `src/main/resources/base/Plugins/Core/core/recycle_bin.py` — finds and
  restores Windows Recycle Bin entries.
