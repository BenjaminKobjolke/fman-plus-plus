# Go to

Jumps a pane to another directory without walking the tree: **GoTo** is a
fuzzy-search prompt on **`Ctrl+P`** (**`Cmd+P`** on macOS), and a set of
palette commands cover the places that are awkward to type — your home
directory, Desktop, AppData, `%TEMP%`.

## Usage

1. Press **`Ctrl+P`** (**`Cmd+P`** on macOS).
2. Start typing. The list is filtered as you go: directories whose *path*
   starts with what you typed rank first, then ones whose *name* does, then
   substring matches, then loose character matches. Type `home` for your home
   directory, `desktop` for the Desktop.
3. Press **`Tab`** to complete the highlighted entry and keep typing below it.
4. Press **`Enter`** (or click) to open it in the active pane.

Suggestions come from the directories you have already visited, ranked by how
often — fman counts every path change in `Visited Paths.json`. Your home
directory, Desktop, Documents and Downloads are always in the list too, even
if you have never opened them in fman. From three characters on it also asks
the OS search index (Windows Search, Spotlight on macOS) for up to ten more
folders whose name starts with your query, so a directory you have never
opened in fman can still show up.

A typed **`~`** is expanded, so `~` alone goes home and `~/Downloads` goes
one below it. Suggestions are displayed tilde-shortened too, unless you are
already typing an absolute path inside your home directory. On Windows, a
path starting with a single backslash (`\Users`) is resolved against the
current drive, and a bare drive letter (`E:`) gets its backslash added.

If the directory you pick has since been deleted, fman drops it from
`Visited Paths.json` instead of showing an error, so it stops being suggested.

## Incognito mode

Run **Toggle incognito mode** from the command palette to temporarily stop
recording GoTo visits. While it is on, folders you open do not gain visit
counts. Existing GoTo suggestions remain available, and the history already
saved before the toggle stays on disk.

When you quit fman in incognito mode, it keeps the pane folders saved before
you turned the mode on. Turning incognito off returns each pane to the folder
and file it showed when you turned the mode on; if that folder has been deleted,
the pane opens its nearest existing parent. Quitting while incognito is on saves
those same folders for the next start, not folders opened during incognito.
Window size, position and fman version are still saved. Incognito mode is off
again after restarting fman.

The status bar shows a permanent **Incognito** marker while the mode is on,
along with a short message each time it is toggled. Registered pane listeners
also receive the change; see [the plugin API](../PLUGINS_API.md#incognito-mode).

| Command name | Palette label | Hidden search keywords | Default key binding |
|--------------|---------------|------------------------|---------------------|
| `toggle_incognito` | Toggle incognito mode | incognito, privacy, private, folder, history, folder history, visit history | none (palette only) |

## Commands

The GoTo prompt itself:

| Command name | Palette label | Default key binding |
|--------------|---------------|---------------------|
| `go_to`      | Go to         | `Ctrl+P` (`Cmd+P` on macOS) |

One command per well-known destination, all reachable from the
[command palette](../COMMAND_PALLETTE.md) and none bound to a key:

| Command name | Palette label | Goes to | Platform |
|--------------|---------------|---------|----------|
| `go_home` | Go home | `~` | all |
| `go_to_desktop` | Go to desktop | your Desktop | all |
| `go_to_documents` | Go to documents | your Documents | all |
| `go_to_downloads` | Go to downloads | your Downloads | all |
| `go_to_app_data` | Go to AppData | `%APPDATA%`; `~/Library/Application Support` on macOS; `$XDG_CONFIG_HOME` or `~/.config` on Linux | all |
| `go_to_plugins_directory` | Go to fman++ plugins directory | the plugins folder in fman's data directory (`%APPDATA%\fman\Plugins`, `~/Library/Application Support/fman/Plugins`, `~/.config/fman/Plugins`; follows `FMAN_DATA_DIRECTORY`) | all |
| `go_to_temp` | Go to temp | `%TEMP%`, `/tmp` | all |
| `go_to_local_app_data` | Go to local AppData | `%LOCALAPPDATA%` | Windows |
| `go_to_program_data` | Go to ProgramData | `%PROGRAMDATA%` | Windows |
| `go_to_program_files` | Go to Program Files | `%ProgramW6432%` | Windows |
| `go_to_program_files_x86` | Go to Program Files (x86) | `%ProgramFiles%` | Windows |

And the rest of the navigation family, for orientation:

| Command name | Palette label | Default key binding |
|--------------|---------------|---------------------|
| `go_up` | Go up | `Backspace`, `Ctrl+Up` (`Cmd+Up` on macOS) |
| `go_back` | Go back | `Alt+Left` (`Cmd+Left` on macOS) |
| `go_forward` | Go forward | `Alt+Right` (`Cmd+Right` on macOS) |
| `go_to_root_of_current_drive` | Go to root of current drive | `Ctrl+\` (Windows only) |

*Home*, *user profile*, *appdata*, *roaming*, *plugins folder*, *%temp%*, *installed programs*
and friends find these rows too — they are hidden keywords, so the row still
reads "Go home". See
[the command palette](../COMMAND_PALLETTE.md#hidden-search-keywords).

Bind any of them to a key in `Key Bindings.json` like any other command
(see [`docs/KEYBINDINGS.md`](../KEYBINDINGS.md)):

```json
{ "keys": ["Alt+Home"], "command": "go_home" }
```

## Notes

- The OS index is asked once per keystroke. Once a query finds no folders,
  longer queries starting with it skip the index, so typing a long
  non-matching string stays responsive.
- **The everyday four are always offered, but not promoted.** Home, Desktop,
  Documents and Downloads join the suggestion pool with a visit count of
  zero, so typing their name finds them instantly — but on an *empty* query
  they sort below the directories you actually visit, because the list is
  ranked by visit count first. They are a safety net, not a shortcut bar. One
  that does not exist on this machine is left out rather than offered and
  failing on Enter.
- **They match on their name, not just their path.** Each carries a name shown
  on the right of the row — *Home*, *Desktop*, *Documents*, *Downloads* — and
  typing it finds the row even when the path shares no letters with it. This
  is what makes `home` reach `~`, whose displayed path contains no `h`, `o`,
  `m` or `e` at all. A name match ranks by the same rules as a path match, so
  an exact `home` still beats a loose path hit; nothing in the path is
  underlined, because the match wasn't there — the same as a hidden keyword in
  the [command palette](../COMMAND_PALLETTE.md#hidden-search-keywords).
- **They are not written to your visit history.** The four are merged into a
  copy of `Visited Paths.json`, so they never gain counts, never get pruned by
  the 500-entry shrink, and never appear in the file itself.
- **The destination commands exist because GoTo cannot suggest these.**
  GoTo seeds its suggestions with the *non-hidden* subdirectories of your home
  directory, so `AppData` and `ProgramData` — both hidden — never appear, and
  `%TEMP%` lives outside your home directory entirely. Typing the path still
  works; the commands just give it a name.
- **Desktop, Documents and Downloads are read from the registry**, not assumed
  to sit under `~`. OneDrive's "back up your folders" moves all three into
  `~/OneDrive`, and only
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders`
  knows where they went. Off Windows, and if the value is missing, fman falls
  back to `~/Desktop` and friends.
- **A destination that does not exist is hidden, not broken.** Each command's
  `is_visible()` checks the directory first, so a machine without a Downloads
  folder simply has no *Go to downloads* row — the palette never offers a jump
  that would fail on Enter.
- **They open in the active pane**, through the same `open_directory` command
  GoTo uses, which reports an unreadable directory gracefully instead of
  raising.
- **The onboarding tutorial still teaches `~`.** Typing it into GoTo remains
  the fastest route home once your hands are already on `Ctrl+P`; *Go home*
  is the discoverable one.

## Implementation

- Destination commands: `Plugins/Core/core/commands/places.py`
  (`_GoToDirectory` and its subclasses)
- GoTo prompt and listener: `Plugins/Core/core/commands/goto.py`
  (`GoTo`, `GoToListener`, `_with_well_known_dirs`)
- Suggestion engine: `Plugins/Core/core/suggest_locations.py`
  (`SuggestLocations`, `unexpand_user`)
- Where the everyday four actually live, and their names (registry-backed):
  `Plugins/Core/core/commands/util.py` (`get_well_known_dirs`,
  `shell_folder`) — shared by GoTo and the palette commands
- `go_up` / `go_back` / `go_forward` / `go_to_root_of_current_drive`:
  `Plugins/Core/core/commands/navigation.py`
- Hidden keywords: `Plugins/Core/Command Keywords.json`
- Default bindings: `Plugins/Core/Key Bindings.json` and
  `Key Bindings (Windows|Mac|Linux).json`
- Visit counts: `Visited Paths.json` in fman's data directory, capped at 500
  paths and shrunk to 250 when it grows past that
- Tests: `Plugins/Core/core/tests/commands/test_places.py` and
  `test_goto.py`
