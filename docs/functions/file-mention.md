# File mention (`@`)

Finds files and folders below the current folder by name, like the `@` file
picker of coding agents. The popup works like the Command Palette: its input
starts with `@`, and the rows show paths relative to the current folder
(`CLAUDE.md`, `tools/CLAUDE.md`, `tickets/17057/plan.md`).

## Usage

1. Press **`@`** in a pane. Typing `@` at the start of Go To switches here too.
2. Type part of a name. Entries whose name starts with what you typed rank
   first, then entries whose relative path contains it. Several words separated
   by spaces must each appear in the path, in any order: `pdf ryd` finds
   `ryd/invoice.pdf`. Last come loose letter matches (`md` finds
   `mod_loader.py`), but only for a single word and only in the name, not in
   the folders above it. Folders end in `/`.
3. Press **`Enter`**. On a file, the pane opens the file's folder and puts the
   cursor on the file. On a folder, the pane opens that folder.

Delete the `@` to switch to Go To with the remaining text. The Go To shortcut
switches as well.

Binding the bare `@` key means `@` can no longer be typed into the pane's live
filter (see [KEYBINDINGS.md](../KEYBINDINGS.md)). Rebind `file_mention` if you
need it there.

## Indexing

The index is built each time the popup opens, on a background thread, and the
list grows while it runs. Folders are read level by level: first the current
folder, then the first level of every subfolder, then the next level, and so
on. Near files therefore show up first, and a deep subfolder cannot hold up
the rest. The walk stops when the popup closes, and after 200,000 entries.
Junctions and symbolic links to folders are listed but not entered.

The popup only works in local and network folders (`file://`), not inside
archives or on FTP.

## Settings

`file_mention_excluded` in `Core Settings.json` lists folder names that are
neither listed nor entered, compared without case. Default:

```json
"file_mention_excluded": [".obsidian", ".git", ".trash", ".stfolder", ".stversions", "node_modules"]
```

Changes apply the next time the popup opens.

Use **Exclude folder from @ file search** to add a folder name to this list,
or **Remove folder from @ file search exclusions** to remove one. Both commands
write the user's `Core Settings.json`.

## Implementation

| Command name | Palette label | Default key binding |
|--------------|---------------|---------------------|
| `file_mention` | File mention | `@`; on Windows also `Ctrl+Alt+@` (AltGr+Q on a German keyboard) |

- `core/commands/file_mention.py`: the command and the row ranking
  (`suggest_mentions`, built on `core/quicksearch_matchers.py`).
- `core/file_mention_index.py`: the level-by-level walk (`FileMentionIndex`).
- `core/palette_switch.py`: the `@` marker and the switch to and from Go To.
