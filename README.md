# fman++

**A file manager you drive entirely from the keyboard.**

Preview text, images and video *inside* the pane. Step into a `.zip` like it's
a folder. Run any command from a fuzzy palette. Extend it in Python.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Windows installer](https://img.shields.io/badge/Windows-signed%20installer-0078d4.svg)](https://github.com/BenjaminKobjolke/fman/releases/latest)
[![macOS disk image](https://img.shields.io/badge/macOS-disk%20image-555.svg)](https://github.com/BenjaminKobjolke/fman/releases/latest)

### [⬇ Download for Windows](https://github.com/BenjaminKobjolke/fman/releases/latest)

no license key, no trial, no nag screen

*macOS: download `fman.dmg` from the [Releases page](https://github.com/BenjaminKobjolke/fman/releases/latest).*
*Linux: [build from source](#build-from-source).*

## See it work

https://github.com/user-attachments/assets/a2d9524b-1c91-4a82-ad79-29786b0243b4

The whole tour is driven from the keyboard. The mouse is never touched.

| | |
|---|---|
| Two panes, one keyboard | select with `Ins`/`Ctrl+A`, copy across with `F5`, type to filter, `Ctrl+F1`/`Ctrl+F2` to sort |
| Organize in place | `F7` new folder, `F6` move into it, `F2` rename |
| Preview inside the pane | images with zoom, text you can edit and save, each viewer with its own command palette |
| Video that actually plays | pause, seek and volume in-pane - and previewing into the *other* pane while you keep browsing |
| Archives are just folders | pack with `Alt+F5`, `Enter` to step inside the zip, `F5` to copy back out |

| Panes | Internal viewer | Filter | Select all |
|---|---|---|---|
| ![panes](media/demos/overview/panes.png) | ![internal viewer](media/demos/overview/view-image.png) | ![filter](media/demos/overview/filter.png) | ![select all](media/demos/overview/select-all.png) |

## What you get

**Navigate.** `Ctrl+P` jumps to any folder by fuzzy name, with tab-completion
and your visited paths ranked first. `Alt+←`/`Alt+→` walk your history.
`Alt+F1`/`Alt+F2` list drives, `Ctrl+\` goes to the drive root,
`Ctrl+→`/`Ctrl+←` push a folder into the other pane. Panes update themselves
when files change on disk. → [KEYBINDINGS.md](docs/KEYBINDINGS.md)

![Go to: press Ctrl+P, type a fragment, tab-complete, jump](media/demos/features/goto.gif)

**Move files.** `F5` copy and `F6` move across panes, with progress, conflict
prompts and cancel. `F7` new folder, `F2` rename, `Shift+F5` symlink.
`F8` goes to the recycle bin, `Shift+Del` doesn't. Explorer's clipboard works
(`Ctrl+C`/`X`/`V`), so does drag & drop. `F11` copies paths, `Ctrl+.` toggles
hidden files, and *Compare directories* selects whatever the other pane is
missing.

**Preview without leaving.** Text, image and video viewers open *in the pane*,
not in another app. Each has its own command palette and its own rebindable
keys, and you can step to the next file without going back to the list. Text
opens read-only, switches to editable, and saves — with **tail mode that
follows a growing log**. Images zoom; video seeks and remembers its volume.
→ [FILE_VIEWERS.md](docs/viewers/FILE_VIEWERS.md)

![Tail mode: the text viewer following a log while it grows](media/demos/features/tail.gif)

**Archives are folders.** `.zip`, `.7z` and `.tar` open with `Enter`, and you
can copy in and out of them like any directory. `.rar` files also open for
browsing and copying files out; they are read-only. fman bundles 7-Zip 26.00
(`7z.exe` on Windows, `7zz` on macOS and Linux; Arch uses the system binary).
On Windows this is **~6× faster than it was**, with a progress bar that actually
moves: a 62 MB, 992-file zip went from 9.8 s to 1.7 s. → [ARCHIVES.md](docs/ARCHIVES.md)

**Make it yours.** 11 bundled themes, switched live from the palette, no
restart. Your own theme is one small JSON file of colors; fonts and padding
live in a `Theme.css` override file. Plus window transparency, pane font zoom
(`Alt+↑`/`Alt+↓`), toggleable columns, single-pane mode, and every key
rebindable.
→ [THEMES.md](docs/THEMES.md) · [COMMAND_PALLETTE.md](docs/COMMAND_PALLETTE.md)

**Extend it in Python.** Plugins add commands, columns, listeners — even whole
filesystems, which is how FTP and process browsing work below. Install one
**from inside fman++**: it searches GitHub and loads the plugin without a
restart. → [Plugins](#plugins)

**Fits your desktop.** Opening a folder from Explorer or the command line
reuses the window you already have. On Windows, network shares stay responsive
instead of freezing the UI. Release notes are translated into 40 languages and
readable in-app. → [SINGLE_INSTANCE.md](docs/SINGLE_INSTANCE.md) ·
[WINDOWS_NETWORK_SUPPORT.md](docs/WINDOWS_NETWORK_SUPPORT.md)

From cmd, run `fman [left [right]]` to open folders; with no arguments it opens
the current folder.

**Script it.** Read pane state and run allowed fman commands from local
scripts over the authenticated HTTP API. → [SCRIPTING_API.md](docs/SCRIPTING_API.md)

Full shortcut reference:
**[workflow-tools.com/fast-file-manager/help/keybindings](https://workflow-tools.com/fast-file-manager/help/keybindings)**

## Themes

Thirteen bundled themes — Monokai, Dark, Light, Solarized Dark/Light, Nord,
Dracula, Gruvbox Dark, High Contrast, WezTerm, Matrix, Windows 11 Light/Dark.
Run *Select theme* from
the command palette; it applies immediately, no restart.

![themes](media/demos/themes/themes.gif)

Writing your own is one JSON file listing only the colors you want to change.
Fonts, padding and one-off color pins go in a user `Theme.css` that loads last
and wins over every theme — see [THEMES.md](docs/THEMES.md).

## Plugins

fman++ is extensible in Python, and installs plugins **from inside the app**: run
*Install plugin* from the command palette and it searches GitHub, downloads and
hot-loads it. Plugins can add commands, columns, context-menu entries and
entire filesystems.

These are the ones maintained on this account.

### [FMAN-MatrixRain](https://github.com/BenjaminKobjolke/FMAN-MatrixRain)

| | |
|---|---|
| The film's digital rain inside a pane, in your theme's colours. One pane, both panes, or as an idle screensaver. | <a href="https://github.com/BenjaminKobjolke/FMAN-MatrixRain"><img src="media/demos/plugins/matrix-rain.gif" width="420" alt="Matrix rain filling one pane, then both"></a> |

### [fman-xd-plugins](https://github.com/BenjaminKobjolke/fman-xd-plugins)

| | |
|---|---|
| Grab bag: copy paths to clipboard, a cross-folder file list for batch copy/move, duplicate, create symlink. |  |

### [QuickLook-Win](https://github.com/BenjaminKobjolke/QuickLook-Win)

| | |
|---|---|
| Preview the selected file with [QuickLook](https://pooi.moe/QuickLook/) via `Space`. Windows only. |  |

### [FMANEverythingSearch-Windows](https://github.com/BenjaminKobjolke/FMANEverythingSearch-Windows)

| | |
|---|---|
| Search files with Everything (voidtools). Windows only. |  |

### [JustSearch](https://github.com/BenjaminKobjolke/JustSearch)

| | |
|---|---|
| Find files and folders below the current directory by words, wildcards, regex, fuzzy match or file content. Results in their own window or flat in the pane. Replaces FuzzySearchFilesInCurrentFolder and fman-search-window-2022. |  |

### [FMAN-FilterByDate](https://github.com/BenjaminKobjolke/FMAN-FilterByDate)

| | |
|---|---|
| Filter the current directory down to files from today or the last X days. |  |

### [FManPowerRenamerAndReplacer](https://github.com/BenjaminKobjolke/FManPowerRenamerAndReplacer)

| | |
|---|---|
| Rename many files at once via search and replace. |  |

### [FManDuplicateFilesAndIncrementExtension](https://github.com/BenjaminKobjolke/FManDuplicateFilesAndIncrementExtension)

| | |
|---|---|
| `Ctrl+D` duplicates the selected file and bumps its index (`NAME_0001.ext`). |  |

### [FManSyncSelectedFilesToOtherPaneForWindows](https://github.com/BenjaminKobjolke/FManSyncSelectedFilesToOtherPaneForWindows)

| | |
|---|---|
| Sync the selected files to the other pane using robocopy. Windows only. |  |

### [FMAN-Favorites](https://github.com/BenjaminKobjolke/FMAN-Favorites)

| | |
|---|---|
| Favorite directories, shareable across machines through placeholder paths. |  |

### [FMAN_FTPClient](https://github.com/BenjaminKobjolke/FMAN_FTPClient)

| | |
|---|---|
| Browse FTP servers as a filesystem (ftputil). Downloads and uploads run 3 files at once; add or remove workers in the progress dialog. |  |

### [fman-media-file-explorer](https://github.com/BenjaminKobjolke/fman-media-file-explorer)

| | |
|---|---|
| Browse phones paired with the Media File Explorer desktop companion via `Show phones`: copy files and folders between phone and PC, create, rename and delete on the phone. The companion asks once for approval. |  |

### [FmanSevenZipTools](https://github.com/BenjaminKobjolke/FmanSevenZipTools)

| | |
|---|---|
| 7-Zip archive commands (fork of alphaniner's, with the debug features that broke on other machines removed). |  |

### [ProcessFS](https://github.com/BenjaminKobjolke/ProcessFS)

| | |
|---|---|
| Browse and kill running processes via the `Show processes` command. |  |

### [TortoiseGit4Fman](https://github.com/BenjaminKobjolke/TortoiseGit4Fman)

| | |
|---|---|
| Run TortoiseGit commands on the current file or folder. Windows only. |  |

### [FMANGoWezTerm](https://github.com/BenjaminKobjolke/FMANGoWezTerm)

| | |
|---|---|
| Open WezTerm in the current directory. |  |

### [FMANGoConemu](https://github.com/BenjaminKobjolke/FMANGoConemu)

| | |
|---|---|
| Open ConEmu in the current directory (`Alt+Shift+C`), and map the current network path to a drive letter. |  |

### [FMANLaunchScriptsForWindows](https://github.com/BenjaminKobjolke/FMANLaunchScriptsForWindows)

| | |
|---|---|
| Launch scripts from a configured scripts directory. |  |

### [FManSharexExtension](https://github.com/BenjaminKobjolke/FManSharexExtension)

| | |
|---|---|
| Send the selected file to ShareX. Windows only. |  |

### [FmanSaveAsDialogExtension](https://github.com/BenjaminKobjolke/FmanSaveAsDialogExtension)

| | |
|---|---|
| Use fman++'s last-used directories inside the Windows Save-As dialog. Windows only. |  |

## Documentation

| Doc | Topic |
|---|---|
| [ARCHIVES.md](docs/ARCHIVES.md) | `.zip`, `.7z`, `.tar` and read-only `.rar` archives browsed like folders with 7-Zip 26.00 |
| [COPY_AND_MOVE.md](docs/COPY_AND_MOVE.md) | Copy and Move: gathering and transferring at the same time, parallel workers |
| [COMMAND_PALLETTE.md](docs/COMMAND_PALLETTE.md) | The `Ctrl+Shift+P` palette |
| [COMMAND_PALETTE_KEYBINDINGS.md](docs/COMMAND_PALETTE_KEYBINDINGS.md) | Rebinding a shortcut from the palette with `Shift+Enter` |
| [COMMAND_PALETTE_KEYWORDS.md](docs/COMMAND_PALETTE_KEYWORDS.md) | Hidden search keywords, and editing them with `Shift+Enter` |
| [DEMOS.md](docs/DEMOS.md) | How the demo recordings are made |
| [DRAG_TO_APP.md](docs/DRAG_TO_APP.md) | Pick from the last 5 apps with Enter or cancel with Esc before dragging via `windrop` |
| [DEMOS_PLUGINS.md](docs/DEMOS_PLUGINS.md) | Recording a demo of a third-party plugin |
| [FONTS.md](docs/FONTS.md) | The bundled font families, picking one, adding your own |
| [ICONS.md](docs/ICONS.md) | File icon sets, icon size, writing your own |
| [KEYBINDINGS.md](docs/KEYBINDINGS.md) | Default key bindings |
| [LARGE_DIRECTORIES.md](docs/LARGE_DIRECTORIES.md) | How a pane loads tens of thousands of entries without stalling the window |
| [PLUGINS.md](docs/PLUGINS.md) | Installing, reloading and removing plugins; duplicate package names |
| [PLUGINS_API.md](docs/PLUGINS_API.md) | Writing a plugin: layout, registration, panes, viewers |
| [ROBOCOPY.md](docs/ROBOCOPY.md) | Copy and Move with robocopy (Windows): destination picker, progress, logs |
| [STATUSBAR.md](docs/STATUSBAR.md) | The bar at the bottom: what it says, hiding it, theming it |
| [SINGLE_INSTANCE.md](docs/SINGLE_INSTANCE.md) | Reusing a running window, and the `single_instance` setting |
| [SCRIPTING_API.md](docs/SCRIPTING_API.md) | Read fman state and run allowed commands from scripts |
| [THEMES.md](docs/THEMES.md) | Theme files, color tokens and switching |
| [TUTORIAL.md](docs/TUTORIAL.md) | The onboarding tour: where its bubble sits, who owns the keyboard, writing a step |
| [WINDOWS_NETWORK_SUPPORT.md](docs/WINDOWS_NETWORK_SUPPORT.md) | UNC paths, network drive icons |
| [WINDOW_FUNCTIONS.md](docs/WINDOW_FUNCTIONS.md) | Window-level functions: chrome toggles, opacity, the dim behind dialogs, centering |
| [WINDOW_TITLE_AND_BARS.md](docs/WINDOW_TITLE_AND_BARS.md) | Window title format, hiding the title bar (and, on macOS, the Help menu) |
| [PURCHASING.md](docs/PURCHASING.md) | Why there is nothing to buy |
| [CREATE_NEW_RELEASE.md](docs/CREATE_NEW_RELEASE.md) | Release process |
| [CREATE_NEW_RELEASE_MAC.md](docs/CREATE_NEW_RELEASE_MAC.md) | Build and publish the macOS disk image |

A searchable, mobile-friendly reference of all keyboard shortcuts is online at
**[workflow-tools.com/fast-file-manager/help](https://workflow-tools.com/fast-file-manager/help/)**.
It is generated by its own repo,
[fman-web-help-system](https://github.com/BenjaminKobjolke/fman-web-help-system),
which regenerates its data from this repo's source; point its `fman_repo_dir`
config at a local fman++ checkout.

## Build from source

Needed on Linux and for developing fman++ itself. fman++ currently uses
Python 3.14.

fman++ uses the [fman build system](https://build-system.fman.io/) (fbs).
Dependencies are managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml`
+ `uv.lock`). uv also installs Python 3.14 if your machine does not have it.
Install uv first ([other methods](https://docs.astral.sh/uv/getting-started/installation/)):

    # Windows (PowerShell)
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh

Get the source:

    git clone https://github.com/BenjaminKobjolke/fman-plus-plus.git
    cd fman-plus-plus

Create the `.venv`:

    install.bat     # Windows: fetch fbs Pro, uv sync, then the unit tests

    # macOS / Linux
    uv run --no-project python tools/fbs_pro.py
    uv sync

Then run it:

    start.bat                    # Windows
    uv run python build.py run   # any OS

`update.bat` re-resolves `uv.lock` and syncs. Call `uv run python build.py`
without arguments to see a list of available commands.

The Linux Docker images (`build.py buildvm <distro>`) still install with pip from
`requirements/*.txt`. Those files are generated, not committed: run
`uv run python build.py requirements` before `buildvm`. For uv, fbs Pro is
downloaded into `vendor/` (see [vendor/README.md](vendor/README.md)).

The video viewer needs the native `libmpv` library. On Windows fman++ downloads
it on first use; on macOS install it with `brew install mpv`, on Debian/Ubuntu
with `apt install libmpv2`.

Run the automated tests with `tools\run_tests.bat` (Windows) or
`uv run python build.py test`. On Windows this requires
Developer Mode (Settings -> System -> Advanced) to be enabled, or some tests
related to symlinks will fail.

## License

MIT — see [LICENSE](LICENSE).

Upstream fman is commercial software. This fork **removed** that machinery
rather than disabling it: the license validator, the nag screen, the
`NOT REGISTERED` title marker and the licensee-email telemetry ping are all
deleted. Every installation is fully activated, and nothing phones home. See
[PURCHASING.md](docs/PURCHASING.md).
