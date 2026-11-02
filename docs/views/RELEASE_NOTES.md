# Release notes

An in-app way to browse fman's release notes, newest release first, without
leaving the app or opening a browser. Picking a release renders its notes
read-only inside the active pane's [text viewer](TEXT_VIEWER.md), the same
in-pane widget used by [View file](../functions/view-file.md).

## Usage

1. Open the command palette and run **"Release Notes"**.
2. A quicksearch list shows every bundled release, newest first, labeled
   plain version labels such as `1.8.0` (older `<version>_<build>` labels remain
   supported), with the date as a hint. Type to fuzzy-filter, just
   like any other palette list.
3. Pick a release (Enter, or click). Its title, version label and date,
   and notes (one bullet per entry) fill the active pane, the same way
   [View file](../functions/view-file.md) does — Escape/Enter/Backspace
   closes it and returns to the file list.

## Commands

| Command name        | Palette label | Keywords                              | Default key binding |
|----------------------|---------------|----------------------------------------|----------------------|
| `show_release_notes` | Release Notes | show release notes, changelog, what's new | none (palette only)  |

The other words listed under *Keywords* are hidden search terms: they find
the command in the palette without ever being shown. See
[the command palette](../COMMAND_PALLETTE.md#hidden-search-keywords).

Can be bound to a key in `Key Bindings.json` like any other command, e.g.:

```json
{ "keys": ["Ctrl+Alt+R"], "command": "show_release_notes" }
```

## Behaviour

- **Hidden when there's nothing to show.** The command doesn't appear in the
  palette at all if no `release_notes/` folder is bundled with this build, or
  it's empty — no dead entry, no empty picker.
- **Newest first, numeric sort.** Releases are sorted by version, then legacy
  build number, with plain versions treated as build zero. This keeps old
  `1.7.13_8` releases readable while placing `1.8.0` above them.
- **Release data.** New en.json files use version, date, title, and notes; they
  do not need a build field.
- **Locale-aware, with English fallback.** The notes shown are for the
  system's detected UI language when that release has a translation for it;
  otherwise `en.json` is used, since English is always authored for every
  release (see [`docs/CREATE_NEW_RELEASE.md`](../CREATE_NEW_RELEASE.md)). The
  release picker's date hint always reads `en.json` — it's just a stable
  sorting aid, not something that needs translating per keystroke.
- **Always read-only.** Unlike [View file](../functions/view-file.md), there
  is nothing backing this text on disk to save to, so the viewer never offers
  *Edit file* here — see [Editing](TEXT_VIEWER.md#editing) for why that
  distinction exists in the viewer itself.
- **Plain text rendering.** Notes are shown as `title`, then the folder's release
  label and date, then one `•`-prefixed bullet per note — no
  markdown, consistent with the text viewer showing everything as raw text.

## Implementation

- `src/main/resources/base/Plugins/Core/core/release_notes.py` — pure (no Qt)
  logic, so it's testable without a live fman instance:
  - `release_notes_dir()` — locates the bundled `release_notes/` folder
    (frozen build or bundled source tree), falling back to the project
    root's own `release_notes/` so it's also found when running from source
    before any freeze/bundling step has run.
  - `list_releases(dir)` — parses plain `<version>` and legacy
    `<version>_<build>` folder names and returns them sorted newest-first.
  - `load_release(dir, locale_code)` — loads `<locale>.json`, falling back to
    `en.json` when that locale's file doesn't exist for this release.
  - `render_notes(data)` — formats a loaded release into the plain text shown
    in the viewer.
- `src/main/resources/base/Plugins/Core/core/commands/release_notes.py` —
  `ShowReleaseNotes` (`DirectoryPaneCommand`), the fman/Qt-facing glue: builds
  the quicksearch list from `list_releases`, resolves the system locale via
  `python_localization.detection.detect_system_language` (imported lazily so
  a missing/broken install of that dependency can't stop Core's other
  commands from loading), and calls `show_text_in_viewer` on the chosen
  release's rendered notes. `is_visible()` returns `False` when no releases
  are found.
- `src/main/resources/base/Plugins/Core/core/textviewer.py` —
  `show_text_in_viewer(pane, text)`, a read-only sibling of `show_text_viewer`
  that mounts arbitrary text with no backing file, instead of reading one
  from disk. Both share their pane-mounting logic (confirm-close, palette
  colors, layout swap, focus proxy) via
  `src/main/resources/base/Plugins/Core/core/textviewer_pane.py` — see
  [`docs/views/TEXT_VIEWER.md`](TEXT_VIEWER.md#implementation) for the rest
  of the viewer's implementation.
- Bundling: `release_notes/<version>/<locale>.json` is used for new releases;
  existing `<version>_<build>` folders remain readable. The notes live at the
  project root (authored per release, see
  [`docs/CREATE_NEW_RELEASE.md`](../CREATE_NEW_RELEASE.md)), outside
  `src/main/resources/base/` where fbs auto-bundles from — so `freeze()` in
  `src/build/python/build_impl/windows.py` copies it into the frozen output
  explicitly via `_copy_release_notes()`. The app imports
  `python-localization` through `fman.impl.localization`, so PyInstaller
  bundles it in `_internal`; Core's lazy import resolves to that copy, and a
  second copy in the Core plugin triggers the duplicate-package alert.
- Tests: `core/tests/test_release_notes.py` covers the pure logic above
  (folder parsing/sorting, locale fallback, rendering);
  `core/tests/commands/test_release_notes.py` is a smoke test for the
  command's aliases and `is_visible()`. The picker dialog itself and the
  viewer actually rendering on screen are Qt-specific and were verified
  interactively, the same as the rest of the text viewer (see
  [`docs/views/TEXT_VIEWER.md`](TEXT_VIEWER.md#implementation)).
