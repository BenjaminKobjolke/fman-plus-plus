# Command palette keywords and names

A command in the [command palette](COMMAND_PALLETTE.md) is findable by words
that are **not** in its name — and it can be renamed to a name of your own
(below). Typing *transparency* selects the row that still
reads **Set window opacity**; typing *zip* finds **Pack**. These hidden
keywords are never displayed — they only widen what finds a command.

fman ships a set of them, and you can add your own: either from inside the
palette (below) or by editing the JSON file by hand.

## Editing keywords from the palette

Open the palette (`Ctrl+Shift+P`), find the row you want, then press
**Shift+Enter** (or click **⋯** on the selected or hovered row) instead of
Enter. Enter runs a command; Shift+Enter opens the *More actions* menu.

Three screens, each a normal fuzzy-searchable list:

| Screen | What it offers | Enter | Escape |
|--------|----------------|-------|--------|
| **Entry menu** | *Change keywords for "…"*, *Change key bindings for "…"*, *Rename to…*, *Reset name* | opens the keyword list or the [shortcut list](COMMAND_PALETTE_KEYBINDINGS.md), asks for a new name, or drops the rename | back to the palette |
| **Keyword list** | *Add keyword…*, then one row per keyword | *Add* asks for a word; a keyword opens the menu below | back to the palette |
| **Keyword menu** | *Delete*, *Go back* | deletes the keyword, or returns | back to the keyword list |

Notes:

- The palette **reopens where you left it** when you Escape out of the entry
  menu or the keyword list, with your query and the same row selected — so
  editing a keyword and immediately trying it out is one flow.
- A new keyword is lowercased and trimmed. Empty input and words already in
  the list are ignored.
- Changes apply on the next keystroke. No restart.
- The viewer palettes have the same Shift+Enter, for the viewer
  pseudo-commands (`video_mute`, `viewer_next_file`, …). Every row the three
  built-in viewers ship carries one, so every row is editable; a viewer entry
  added by a plugin that ships no command name has nothing to store keywords
  under and says so in the status bar. The viewer palettes reopen on the query
  you typed, but always with the first row selected — they don't restore the
  row the way the global palette does.
- *Change key bindings* is the third thing this menu edits, and the only one
  that writes a different file per palette — see
  [`docs/COMMAND_PALETTE_KEYBINDINGS.md`](COMMAND_PALETTE_KEYBINDINGS.md).

## Renaming a command

*Rename to…* changes what the row **says**. Rename **Quit** to **Exit** and the
palette lists **Exit** — the command itself, its key binding and its shortcut
hint are untouched.

The old name is not lost: renaming folds the command's original name(s) into
its keywords, so typing `quit` still finds the row. It is a keyword hit now, so
the row shows **Exit** and underlines nothing (see the ranking rules below).

*Reset name* appears in the entry menu only while a rename is in place, and
hands the label back to fman's own.

Renames live in `Command Titles.json` — a flat map of command name to one
label:

```json
{
    "quit": "Exit",
    "video_mute": "Silence"
}
```

Same keys, same per-OS user file and same merge rules as the keyword file
below; fman ships no titles of its own, so an absent file simply means no
renames.

## Where they are stored

`Command Keywords.json` — a flat map of command name to a list of search terms:

```json
{
    "set_window_opacity": ["transparency", "opacity", "alpha"],
    "pack": ["zip", "7z", "tar", "compress"],
    "video_mute": ["sound", "volume", "audio"]
}
```

- **The keys are command names**, the same ones
  [`docs/KEYBINDINGS.md`](KEYBINDINGS.md) uses — viewer pseudo-commands
  included, which is why the global and the viewer palettes read one file.
- **fman's own list** ships in the Core plugin and is never modified.
- **Your edits** land in
  `%APPDATA%/fman/Plugins/User/Settings/Command Keywords (Windows).json`
  (equivalent per-OS `Plugins/User/Settings/` folder elsewhere), next to your
  `Key Bindings (<OS>).json`.
- Unlike key bindings, a command you name in your file **replaces** fman's
  list for that command — the other commands are untouched. That is why the
  in-palette editor always writes the whole list back, fman's terms included:
  adding one keyword keeps the rest working.
- Terms are lowercase, and matched the same fuzzy way names are.

Editing the file by hand still works; the palette picks it up the next time it
opens.

## How a keyword ranks

- **Exact matches come first.** Typing a command's whole name, or a whole
  keyword, puts that row at the very top — which is why *exit* offers **Quit**
  before *Extract to opposite*, whose name happens to contain `e`, `x`, `i`,
  `t` in that order.
- **Otherwise names match first.** A row found by its real name ranks above one
  found only by a keyword.
- **A keyword hit underlines nothing.** The typed characters are highlighted in
  the title only when the title is what matched — a keyword has nothing in the
  row to underline.
- **All loose keyword hits share one bucket**, and inside a bucket rows sort by
  title length, shortest first. So a command whose keyword only barely matches
  can outrank the one you meant.

### A worked example: why *single* offers **Go to AppData**

Add `"single pane"` to `show_only_active_pane`, type `single`, and the first
row is **Go to AppData**:

```
single
> Go to AppData
  Show only active pane
```

Nothing is broken. `go_to_app_data` ships the keyword **`settings folder`**,
and `s`, `i`, `n`, `g`, `l`, `e` appear in that order inside it —
**S**ett**i**n**g**s fo**l**d**e**r — so it is a legitimate fuzzy match. Both
rows matched by keyword, so both are in the same last bucket, and
*Go to AppData* (13 characters) sorts above *Show only active pane* (21).

Two ways to put your row first:

1. **Add the bare word as its own keyword**, so it can match *exactly*:
   `{"show_only_active_pane": ["single pane", "single"]}`. An exact keyword is
   bucket 0 and beats every loose hit. Only applies once the whole word is
   typed — while you are still on `singl`, both rows are loose again.
2. **Pick a keyword that nothing else swallows.** Short, common letter runs
   like `single` are subsequences of a lot of English; a distinctive one
   (`onepane`, `solo`) collides with far less.

The general rule: if a keyword surprises you, look for another command whose
keyword contains your query *as a subsequence* — that, plus the shortest-title
tie-break, explains nearly every unexpected first row.
