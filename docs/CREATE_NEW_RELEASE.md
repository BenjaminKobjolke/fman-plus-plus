# Creating a New Release

fman is built with **fbs** (fman build system — yes, the project that gave fbs its
name). `build.py` at the project root defines the fbs commands; `tools/*.bat` are
thin wrappers around `python build.py <command>`.

A release is identified by its plain semantic version, e.g. `1.8.0`:

- `version` (semver) — `src/build/settings/base.json`, key `"version"`. The release
  tooling bumps it automatically for each release. The patch increments through 10;
  the next release raises the minor and resets the patch to 0 (for example,
  `1.8.10` -> `1.9.0`). There is no build counter.

## One-command release

```bat
tools\release_create.bat             :: the whole release
tools\release_create.bat --internal  :: internal test build: no release notes, INTERNAL commit
tools\release_create.bat --dry-run   :: print the label and every command, run nothing
```

Runs the shared `release-tool create`
([`CREATE_RELEASE_COMMAND.md`](https://github.com/BenjaminKobjolke/release-tool/blob/main/docs/CREATE_RELEASE_COMMAND.md)),
configured by `tools/release_create.ini`. The build asks a running fman to close (step 4).
The script calculates the next version and bumps `base.json` as part of the release.

What it does, in order — the numbered steps below describe each part in detail and
remain the manual path:

1. Computes the next plain semantic version and uses it as the release label.
2. Has Codex author `release_notes/<version>/en.json` if it is missing (step 2).
3. Runs `tools\build_increment.bat` — **the one and only bump of the release**. If
   the build fails, it runs `tools\build_decrement.bat` to roll it back.
4. Runs `tools\translate_release_notes.bat` (step 3).
5. Runs `tools\build_release.bat`: `python build.py release_build`, i.e. clean +
   release profile + freeze, sign, installer, sign the installer. On success it
   records the label in `target\release_version.txt`, next to the installer. The
   build bats use the project's uv venv, `.venv\Scripts\python.exe`
   (`tools\find_build_python.bat`; run `install.bat` once), whatever venv the
   Tickets Watcher puts in front of it.
6. **Asks** `Commit, tag and push <label>?` — `git add -A`, commit
   `RELEASE (fman): <label>`, tag `<label>`, push both.
7. **Asks** `Create GitHub Release <label>?` — only offered if 6 ran. Uploads
   `target\fmanSetup.exe` with the notes from `en.json`, titled `fman++ <label>`.

Both questions default to no; declining leaves a finished, signed build in `target\`.

After publishing the Windows release, build and attach the Mac disk image for
the same label; see [CREATE_NEW_RELEASE_MAC.md](CREATE_NEW_RELEASE_MAC.md).

**The tag is the plain version** (`1.8.0`), not `v<version>` as in releases through
`v1.7.13` or the legacy `<version>_<build>` labels. Older `<version>_<build>` folders
and tags remain readable. Installs at `1.7.13_8` or older cannot recognize plain tags,
so they will not be offered `1.8.0` by the update check and must download it manually.

### Publishing an existing build again

```bat
tools\github_release.bat
```

Publishes the installer that is in `target\` under the label recorded in
`target\release_version.txt` — no rebuild, no bump. Use it when question 7 was
declined or the upload failed. It reads the recorded label rather than the current
version source, so it still publishes the right release after that source has moved
on. It refuses to run without a record, installer, release notes, or a
`<label>` tag on `origin` (commit, tag and push first — step 6 by hand:
`git tag <label>`, `git push`, `git push origin <label>`).

For an installer built before the record existed, name the label, for example:
`tools\github_release.bat 1.8.0`.

`python tools/test_release_version.py` checks this handoff with a fake build and a
fake uploader; run it after changing `build_release.bat` or `github_release.bat`.

## 1. Version

```bat
tools\version_get.bat       :: prints the current version, e.g. 1.7.13
tools\build_increment.bat   :: calculate and write the next version
tools\build_decrement.bat   :: restore the version from the current Git commit
```

These are thin wrappers over `tools\release\build_number.py` (stdlib only, run with
the `.venv` python from `tools\find_build_python.bat`). The helper updates the `version` in
`src/build/settings/base.json`; no separate counter or manual version bump is needed.
The current version is the newer of `base.json` and the highest plain `X.Y.Z` Git tag.
If a version bump is lost (reverted or never committed), the next release continues after the
released tag instead of failing at `git tag` after the build.

The release script calculates the next version before authoring notes. From
`1.7.13`, the next release is `1.8.0`; then `1.8.1` through `1.8.10`, followed by
`1.9.0`. Do not bump or reset anything by hand.

## 2. Release notes directory + `en.json` schema

Create `release_notes/<version>/en.json`:

```json
{
  "version": "1.8.0",
  "date": "YYYY-MM-DD",
  "title": "Short headline",
  "notes": [
    "First user-facing change",
    "Second user-facing change"
  ]
}
```

The actual release text is the **`notes`** array. **Author only `en.json`** — every
other locale is machine-generated (step 3). Do not hand-write any other locale
file.

## 3. Translate (mandatory — do not skip)

Run the project's translator wrapper to generate every other configured locale
from `en.json`:

```bat
tools\translate_release_notes.bat
```

This calls the shared **GPT-json-translator** tool
(`d:\GIT\BenjaminKobjolke\GPT-json-translator`) in recursive mode over the whole
`release_notes\` tree — it fills in only the missing/changed keys for each
`<version>\` folder that has an `en.json`, so it's safe to re-run any
time. Skipping this step means non-English users see no release notes (or stale
ones) for that release.

## 4. Build the release

`tools\release_create.bat` does this step for you through `tools\build_release.bat`
(`python build.py release_build`), which builds on the dirty tree the script leaves
behind — do **not** also increment or run `python build.py release` then. What
follows is the manual path.

`freeze()` (via PyInstaller) deletes and recreates `target/fman/` — a running copy
from that folder locks its files. `tools\build_windows.bat` and
`tools\build_release.bat` (also used by `tools\release_create.bat`) ask that copy
to close and stop with a message naming any process that still holds a file from
the folder. Only `python build.py release` requires you to close it by hand first.

The one-command release flow bumps the version in base.json automatically and
restores it from HEAD if the build fails. For the manual `python build.py release`
path, apply the version bump with the helper before starting the build; the fbs command
may require a clean tree, so commit the version bump first:

```bat
tools\build_increment.bat
git add src/build/settings/base.json
git commit -m "RELEASE: bump version to <version>"
```

The release notes folder and tag must use the bumped version.

```bat
tools\build_windows.bat          :: python build.py freeze  -> target\fman\
tools\build_windows_installer.bat:: python build.py installer -> target\fmanSetup.exe (fbs's own NSIS template)
```

`build.py` also exposes the full fbs pipeline for an actual public release:

```bat
python build.py release
```

`release()` branches on whether `src/build/settings/base.json`'s `version` ends
in `-SNAPSHOT`:

- **`-SNAPSHOT` version** (fbs's original upstream workflow): bumps the settings
  file to the release version, runs `publish()`, tags the commit `v<version>` in
  git, bumps the settings file again for the next `-SNAPSHOT` dev cycle, and
  pushes — fully automatic.
- **Plain version, e.g. `1.8.0`** (this fork's actual convention — the helper bumps it
  and it never carries a `-SNAPSHOT` suffix): `release()`
  just calls `publish()` directly. **No tag, no push happens automatically.**
  After a successful build you must do it yourself before step 4.5 — the tag is
  the plain version:
  ```bat
  git tag <version>
  git push origin main
  git push origin <version>
  ```
  `python build.py release` does not write `target\release_version.txt` (only
  `tools\build_release.bat` does), so pass the version to step 4.5 explicitly.

`publish()` on Windows runs `freeze` → `sign` → `installer` → `sign_installer` →
`upload`. The project owns `src/installer/windows/Installer.nsi`; its visible
names come from the `display_name` build setting. Keep `app_name` as `fman`:
it names the executable, install directory and uninstall key, so existing
installs update in place. **`upload()` is a no-op for this fork** —
`src/build/python/build_impl/windows.py` disabled it (this fork has no access
to the original project's AWS account and doesn't publish to
`update.fman.io`, upstream's channel). Distribution is GitHub Releases only
(step 4.5).

### Signing — XIDA network-share handshake, not fbs's local cert

`sign()` and `sign_installer()` are **overridden** in
`src/build/python/build_impl/windows.py` (imported into `build.py` in place of
fbs's own `fbs.builtin_commands.sign`/`sign_installer`). Reason: fbs's built-in
Windows signing uses a local `signtool` + `src/sign/windows/certificate.pfx`,
and that certificate (`CN=Michael Herrmann`, issued by Sectigo) **expired
2022-07-03** — it can no longer sign anything.

The overridden `sign()`/`sign_installer()` instead call `tools\sign_exe.bat`,
which reuses this org's shared `release-tool` signing handshake
(`D:\GIT\BenjaminKobjolke\release-tool`, `release_tool.pre_signer.PreSigner`):

1. Copies the exe to `\\XIDA-SERVER\SigningExecutables\`.
2. Polls `\\XIDA-SERVER\SigningExecutables\signed\` until the same filename
   appears there, signed by an external signing service watching that share.
3. Verifies the signer's certificate `CN` is `XIDA GmbH`.
4. Copies the signed file back over the original, cleans up both network
   locations.

Requires `uv` on PATH and access to the `release-tool` repo/network share — the
same prerequisites every other XIDA project's `sign_exe.bat` already assumes.
Order matters and is preserved from fbs's original `publish()`: the app exe
(`target/fman/fman.exe`) is signed **before** `installer()` packages it into
`fmanSetup.exe`, and the installer exe is signed **after**.

`tools\build_windows.bat` / `tools\build_windows_installer.bat` (freeze/installer
only, no signing) remain unsigned local test builds — only `python build.py
publish`/`release` produces a signed, shippable build.

**Housekeeping not yet done:** the dead cert (`src/sign/windows/certificate.pfx`)
and its password (`windows_sign_pass` in `src/build/settings/windows.json`) are
still committed and tracked in git history, along with other secrets in
`src/build/settings/base.json` (AWS keys, GPG passphrase, server API secret).
Nothing in this repo calls `fbs`'s signing path anymore, so these are now inert,
but they remain exposed in history. Rotate anything still live and consider
purging history if this repo is or was ever public.

## 4.5. Publish to GitHub Releases

Prereq (one-time): [`gh` CLI](https://cli.github.com/) installed and on `PATH`,
authenticated via `gh auth login` (scope: `repo`).

`tools\release_create.bat` offers this as its last question. By hand — after a
signed `target\fmanSetup.exe` exists and the `<version>` tag is pushed — run:

```bat
tools\github_release.bat            :: label from target\release_version.txt
tools\github_release.bat <version>  :: explicit, for a build without that record
```

This calls the shared `release-tool`'s `github-release` command (same
signing-handshake repo as `sign_exe.bat`, see
[`GITHUB_RELEASE_COMMAND.md`](https://github.com/BenjaminKobjolke/release-tool/blob/main/docs/GITHUB_RELEASE_COMMAND.md))
to create a GitHub Release tagged `<version>` at
[github.com/BenjaminKobjolke/fman/releases](https://github.com/BenjaminKobjolke/fman/releases),
attach `target\fmanSetup.exe`, and set the body from
`release_notes\<version>\en.json`. See "Publishing an existing build again" above
for what it checks first.

Idempotent — re-running re-uploads the asset (`--clobber`) instead of failing. On
that "already exists" path the release-tool does **not** update the title or
body (see `release-tool/src/release_tool/github_publisher.py`,
`_ALREADY_EXISTS_MARKER` branch). To change the notes of a published release:
```bat
gh release edit <label> --repo BenjaminKobjolke/fman --notes-file notes.md
```
(the `en.json` isn't directly Markdown, so render its `title`/`notes` into a
`# title` + bullet-list `.md` file first).

**`release_notes/` is bundled into the frozen app.** fbs auto-bundles
everything under `src/main/resources/base/` into the frozen output
(`target/fman/`), but `release_notes/` lives at the project root (authored per
release, not under `src/main/resources`), so it needs an explicit copy.
`copy_release_notes()` in `src/build/python/build_impl/__init__.py` copies it
next to the frozen `Plugins/` directory on Windows and into
`target/fman.app/Contents/Resources/` on macOS — skipped if no release has been
authored yet. `core.release_notes.release_notes_dir()` (Core plugin) finds it
there at runtime, or falls back to the project-root `release_notes/` when
running from source before any freeze.

## 5. In-app Release Notes view

See [`docs/views/RELEASE_NOTES.md`](views/RELEASE_NOTES.md) for full usage
and implementation details. Summary:

Command **"Release Notes"** (`core/commands/release_notes.py`,
`ShowReleaseNotes`), invokable from the command palette. Lists every release
in `release_notes/`, newest first, via the palette's quicksearch UI; picking
one renders that release's notes read-only in the pane's text viewer
(`show_text_in_viewer`, see `docs/views/TEXT_VIEWER.md`). Hidden
(`is_visible()`) when no `release_notes/` folder is bundled.

Locale is detected via `python_localization.detection.detect_system_language`
(the `python-localization` dependency in `pyproject.toml`), falling
back to `en.json` when a release has no translation for the detected locale,
or when the library itself is missing (defensive `ImportError` catch — Core's
other commands must still load even if this one dependency is broken).
Parsing/sorting/locale-fallback logic lives in `core/release_notes.py`
(pure, unit-tested — see `core/tests/test_release_notes.py`).
