# Changing key bindings from the palette

You don't have to edit a JSON file to rebind a key. Every command in the
[command palette](COMMAND_PALLETTE.md) can be given a shortcut — or have one
taken away — from inside fman, in the same **Shift+Enter** menu that edits a
command's [keywords and name](COMMAND_PALETTE_KEYWORDS.md).

For the files themselves, the merge order, and the full table of defaults, see
[`docs/KEYBINDINGS.md`](KEYBINDINGS.md).

## The three screens

Open the palette (`Ctrl+Shift+P`), find the row you want, then press
**Shift+Enter** instead of Enter and choose *Change key bindings for "…"*.

| Screen | What it offers | Enter | Escape |
|--------|----------------|-------|--------|
| **Entry menu** | *Change keywords*, *Change key bindings*, *Rename to…* | opens the shortcut list | back to the palette |
| **Shortcut list** | *Add shortcut…*, then one row per shortcut | *Add* asks you to press a key; a shortcut opens the menu below | back to the palette |
| **Shortcut menu** | *Remove*, *Go back* | unbinds the shortcut, or returns | back to the shortcut list |

The shortcut list marks where each binding came from:

```
Add shortcut...
Ctrl+Alt+P  (yours)
F5  (default)
```

*(yours)* is a binding from your own file — yours to delete. *(default)* is one
fman ships; removing it works differently (below).

## Adding a shortcut

*Add shortcut…* opens a small dialog and waits for you to **press** the
combination — you never type the string, so there is no way to misspell
`PgDown` or `Num+Down`. Press Escape to back out.

If the combination already runs something else, fman names that command and
asks whether to take the key over:

> `F5` currently runs `copy`. Bind it to "Pack" instead?

Answering yes is honest about what happens: your binding is written to the
**front** of your own file, and fman dispatches the first match it finds, so
yours wins and `copy` loses `F5`. Answering no changes nothing.

Changes take effect immediately — no restart, and no `reload_plugins`.

## Removing a shortcut

Pick a shortcut, then *Remove*. What that means depends on where it came from:

- **One of yours** is deleted from your file outright.
- **A shipped default** cannot be deleted — fman never writes to the files it
  ships. It is *shadowed* instead: removing `F5` writes a binding of `F5` to
  the `do_nothing` command, which is a real command that does exactly that. The
  key stops working, the palette stops advertising it, and you can see why by
  reading your file.

`do_nothing` is invisible in the palette — it is a target for this, not an
action you would ever run.

## Viewer commands

The [viewer palettes](viewers/FILE_VIEWERS.md) have the same Shift+Enter, and
this is where it earns its keep: most viewer commands (`video_mute`,
`viewer_delete_file`, `image_actual_size`, …) ship with **no default key at
all**, so binding them used to mean creating a file by hand.

Viewer bindings are written to `Viewer Key Bindings (<OS>).json`, a separate
file from the global one — see
[the viewer section of `docs/KEYBINDINGS.md`](KEYBINDINGS.md#bindable-viewer-commands)
for why. The editor picks the right file from which palette you opened it in;
there is nothing to choose.

Removing a viewer default (`Space` for play/pause, say) shadows it with
`do_nothing` just like a global one, and the viewer honours that instead of
falling through to its built-in key.

The one exception is the zoom rows — *Increase/Decrease font size* in the text
viewer, *Zoom in*/*Zoom out* in the image viewer. They follow the global pane
font-size shortcut (`increase_pane_font_size`/`decrease_pane_font_size`), which
the viewers read from `Key Bindings (<OS>).json`, so Shift+Enter on them edits
that file instead. Rebinding one there moves the key for the file list and the
viewers together, which is the point: it is one shortcut, not two.

## Where your edits are stored

`%APPDATA%/fman/Plugins/User/Settings/Key Bindings (Windows).json` — the
per-OS user file described in
[`docs/KEYBINDINGS.md`](KEYBINDINGS.md#files-and-load-order), and the same one
you would edit by hand. Viewer bindings land beside it in
`Viewer Key Bindings (Windows).json`. On macOS and Linux the folder and the
`(Mac)` / `(Linux)` suffix change; nothing else does.

The editor only ever writes that one file, so everything it does is reversible
by deleting a line from it. After each write fman reloads its Settings plugin,
which is what makes a new binding live without a restart.

## Two things it can't do

- **Bind Escape.** Escape cancels the capture dialog, so it can never be
  recorded. Add it by hand if you really want it.
- **Spot a differently-spelled duplicate.** Shortcuts are compared as plain
  strings throughout fman, so a hand-written `Shift+Ctrl+P` and a captured
  `Ctrl+Shift+P` look like two unrelated keys — the conflict prompt won't fire
  and both entries stay in the file. The dialog always writes one canonical
  modifier order, so this only bites files you edited yourself.
