# Version
2

# Coding Rules (Pointer)

This project's rules live in two files in the project root:

- `CODING_RULES.md` — code quality and conventions. BINDING for all code work in
  this repository, always.
- `IMPLEMENTATION_FLOW.md` — the end-to-end flow to follow when planning and
  implementing a change (checks, gates, Definition of Done).

MANDATORY: Before writing or editing ANY code, you MUST Read BOTH files in full
**in the current session**. Do not rely on memory of a previous session, a
summary, or partial reads.

If you are about to make a code change and have not read both files in this
session: STOP, read them, then continue.

An external tool may orchestrate the implementation itself. When a skill or run
states that the implementation is orchestrated, ignore `IMPLEMENTATION_FLOW.md`
entirely — the orchestrator runs those steps as its own phases. `CODING_RULES.md`
stays binding either way.

Do not inline rules back into this file and do not use `@import` for either file —
they are intentionally referenced, not imported.


## Planning a new feature: check existing plugins first

For `/tickets:plan` runs about new features or behavior changes, especially `Upstream #<n>: …`
todos, check installed plugins before asking design questions. This does not apply to bug fixes in
existing fman++ code.

Search `%APPDATA%\fman\Plugins\User` and `%APPDATA%\fman\Plugins\Third-party`. For plugins with
matching names, read their README and search their `.py` files for the feature's keywords, such as
command names, protocols or "search". Also run the normal `graphify query` on this repository.
When a plugin already implements some or all of the feature, name it and what it covers in the
first question round, which asks only:

- `build into fman++` — plan the work here;
- `extend the plugin` — move the todo to that plugin's project, when it has one;
- `Nothing left to do, cancel` — offer only when the plugin may cover the whole request, never as
  the default.

Default to `extend the plugin` when it has a project, otherwise `build into fman++`. Ask detail
questions about keys, libraries, UI and credential storage in the next round. If no matching
implementation is found, say so in one line in the plan's Context and plan as usual.

| Plugin folder | Tickets project |
| --- | --- |
| `FMAN_FTPClient` | #12337 |
| `JustSearch` | #12358 |
| `FMAN-Favorites` | #12351 |
| `fman-media-file-explorer` | #12346 |

For other plugins, use `projectsList` to match the project by name; no match means the plugin has
no project.

## Planning questions: offer a setting for taste, performance, access or safety

For `/tickets:plan` design questions about how an fman behavior should work, check whether the
answer is a matter of taste or of performance (refresh timers and intervals, where a message is
shown, live vs. snapshot views, switching a visual cue on or off) or an access or safety choice
(which computers may connect, what a script may do, extra safety checks before file
operations). When it is, always add the option `setting (default: <X>)`, where `<X>` is one of
the other options; for access and safety choices `<X>` is the safest option. Picking it means
the user chooses the behavior in a settings file and the plan names the default value, the key
and the file:

- `Core Settings.json` for Core plugin behavior, read through `get_setting` in
  `core/settings.py` (as `drive_space_refresh_seconds` and `dim_hidden_files` do);
- `%APPDATA%/fman/Local/Settings.json` for app-level behavior and window state (as `theme`,
  `status_bar_visible` and `scripting_api` do).

When the setting is an on/off switch the user may want to change while fman runs, the option
also names a command palette toggle next to the key, so the plan does not need a later change
for it: an `ApplicationCommand` with a `Toggle ...` alias. For an app-level setting it goes in
`src/main/python/fman/impl/plugins/builtin.py` (as `ToggleStatusBar` and `ToggleScriptingApi`
do); for a Core setting it goes in `core/commands/` and saves the value with `save_setting` (as
`ToggleLockedFileCheck` does for `check_locked_files`).

Keep the question's own default as it is; the setting option does not have to be the default.
When the plan prefers one fixed behavior, the question or the plan's Context says in one
sentence why a setting is not needed (for example: correctness, not taste). This does not apply
to bug fixes or to questions with one correct answer.

The plugin-first rule keeps precedence: its first round still asks only the gating question, and
the setting option applies to the detail round that follows.

## Testing

### Checking UI behavior

For fman UI behavior checks, see `docs/UI_AUTOMATION.md` and use
`tools\fman_ui.bat` to launch and drive a throwaway instance.

After touching `tools/fman_ui/**`, run `uv run python tools/test_fman_ui.py`.
After touching `src/main/python/fman/impl/scripting/automation.py` or
`src/main/python/fman/impl/util/qt/key_events.py`, run
`tools\run_automation_tests.bat`.

`tools\run_tests.bat` runs all of `fman_unittest` offscreen (~5 s). The `run_*_tests.bat` watcher commands use `tools\unittest_with_timeout.bat`, which drops the watcher's venv, runs the project's `.venv` python (`tools\find_build_python.bat`) and stops a test after 120 s. `python build.py test` is not a usable check because fbs ignores the result and always exits 0.

For one Core test module, run `tools\run_core_tests.bat core.tests.fs.test_drives`. Never run bare `python` or `pytest` on a test file: fman's dependencies live only in the project's uv `.venv` (`install.bat` creates it), so bare `python` reports `fbs_runtime` missing. Use the bats or `uv run python`.

After touching `tools/close_running_fman.ps1` or `tools/build_windows.bat`, run
`uv run python tools/test_close_running_fman.py`.

After touching `tools/release/build_number.py`, run
`uv run python tools/test_build_number.py`.

After touching `tools/create_media/build_app_icons.py`, run
`uv run python tools/test_build_app_icons.py`.

After touching `src/build/python/build_impl/mac.py`, `tools/sign_mac.sh`,
`tools/build_mac.sh` or `tools/github_release_mac.sh`, run
`uv run python tools/test_build_mac.py`.

The script asks a running fman to close via the registered window message
`fman.CloseForBuild`; fman (`src/main/python/fman/impl/build_shutdown.py`)
answers with an Esc-cancelable countdown. After touching that module, run
`tools\run_build_shutdown_tests.bat` (a `*_test.py` like the MessageBox tests:
`show()` aborts under the offscreen platform, so the test plays the countdown
without showing it).

After touching `fman/impl/update_check.py`, run
`uv run python -m unittest fman_unittest.impl.test_update_check` with `PYTHONPATH` set
to `src\main\python;src\unittest\python`. The Core update check and command
are covered by `run_core_tests.bat`.

After changing Core plugin code (`src/main/resources/base/Plugins/Core/core/**`),
run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_core_tests.bat'"
```

Fast (~0.4s), covers all of `core`'s own tests. Do **not** use `python build.py test`
for this — it also runs fbs's bundled `fman_unittest`/`fman_integrationtest` suites,
which have a known intermittent hang (Qt/thread state leaking from
`fman_integrationtest.test_qt` into a later widget test — unrelated to Core plugin
changes, not yet root-caused).

If you touched the zip/7-Zip filesystem code (`core/fs/zip.py` or
`core/tests/fs/zip_test.py`), also run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_zip_tests.bat'"
```

These are excluded from `run_core_tests.bat` (filename doesn't match `test*.py`)
because they spawn `7za.exe` as a real subprocess and can hang under
AV/EDR interference.

If you touched the pane model (`src/main/python/fman/impl/model/**` — sorting,
filtering, or where an added/renamed/changed row is inserted), run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_model_tests.bat'"
```

If you touched dialog widgets (`src/main/python/fman/impl/widgets.py` —
`MessageBox` sizing/alignment — or the `QMessageBox` rules in
`src/main/resources/base/styles.qss`), run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_messagebox_tests.bat'"
```

If you touched the progress dialog's worker rows
(`src/main/python/fman/impl/workers_label.py`, or `ProgressDialog` in
`src/main/python/fman/impl/progress_dialog.py`), run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_progress_dialog_tests.bat'"
```

Like `run_overlay_focus_tests.bat`, these live in a `*_test.py` file that
`python build.py test` deliberately does not discover: they need a
`QApplication` of their own, and stray Qt state is what makes that suite hang.

If you touched the file list's row heights
(`src/main/python/fman/impl/view/uniform_row_heights.py`, or the vertical
header set up in `src/main/python/fman/impl/view/__init__.py`), run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_view_tests.bat'"
```

Same `*_test.py` arrangement. The header is `Fixed` on purpose: in
`ResizeToContents` Qt re-measured every row on each background-load commit,
which stalled the GUI thread in directories with tens of thousands of entries.

How fman drives 7-Zip (the `-bsp1` progress protocol, canceling, why there is
no pseudo-terminal on Windows) is documented in `docs/ARCHIVES.md`.

After touching `src/main/resources/base/Plugins/Robocopy/**`, run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_robocopy_tests.bat'"
```

When `windows.py`, `planner.py` or `jobs.py` changed, also run:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_robocopy_integration_tests.bat'"
```

The integration runner spawns real `robocopy.exe`, so its `*integration_test.py`
files are excluded from the unit-test pattern, like the zip tests.

## Code Analysis

Two analysis modes — pick by situation:

**Changed-files run (default after implementing a feature, finishing a plan, or
fixing a bug):**

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\analyze_changed_and_new_files.bat'"
```

Uses `--only-changed`: the report is filtered to files new/modified vs git `HEAD`
(includes untracked). Project-wide analyzers still run; only the report is
filtered. Fast feedback, no noise from pre-existing violations elsewhere.

**Full run (whole-project audits):**

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\analyze_code.bat'"
```

Use the full run for: an explicit audit request (`/analyze:run-and-fix`),
exception maintenance (`/analyze:improve-exceptions`), before a release/merge,
after refactors that touch shared code, or when the working tree is clean vs
`HEAD` (a changed-files run would report nothing).

Results are written to `code_analysis_results/` as **per-rule CSV files** (e.g.
`flutter_analyze.csv`, `line_count_report.csv`, `duplicate_code.csv`) — there is
no `.md` report, and a missing CSV means that rule found nothing. Fix any
reported issues before committing.

### Analyzer findings and exclusions

The run exits 1 only for ERROR findings: Ruff `E…` codes and files above the
line-count `error` threshold. Ruff `F`/`W` findings and duplicate matches are
warnings. `E101` and `E731` are ignored alongside `W191`: upstream uses tabs
with aligned continuation lines and `name = lambda`; do not reformat those files
just to satisfy Ruff.

Ruff excludes use bare directory names because `target/**` does not exclude the
build output on this machine. The console's Ruff finding count is capped at 50
in the full run and 5 in the changed-files run, so it is not the total.

### `tools/fix_ruff_issues.bat` — safe now, but it only adds newlines

It used to break the build: ruff's F401 autofix deleted `from .zip import *`
(`core/fs/__init__.py`, how the 7-Zip filesystem registers) and
`viewer_for_category` from `core/viewers.py` (re-exported to
`core/viewer_navigation.py`), erroring 4 Core tests. cli-code-analyzer now
force-ignores F401/F403/F405/F811 for fix runs, so this can't recur.

What remains is 146 changes across 121 files that are all trailing
newline-at-EOF, most of them in upstream fman source. Zero functional gain,
guaranteed conflicts on any upstream merge — so running it is still not worth
it here. `/analyze:run-and-fix` says to run a fixer bat first; skip it and run
only `analyze_code.bat`.

Note `--unsafe-fixes` is off, which is what keeps the codebase-wide
`except ValueError as file_disappeared:` idiom intact — the unused name
documents *why* the exception is expected. Do not turn it on.

## Knowledge Graph (graphify)

This project's graph is built from the **repository root**, never from `src/`:

```bash
/graphify . --directed
```

The graph deliberately covers `docs/`, `tools/`, `build.py` and the root
`*.md` files as well as `src/` — roughly 480 of its ~4000 nodes, and the half
that answers "how does X work" rather than "where is X defined". Rebuilding
with a narrower path deletes them. graphify's shrink guard catches that and
refuses the write; **do not force past it** — re-run with `.` instead.

Excluding `docs/` from `.graphifyignore` is the same mistake in another form,
and it has been tried: a code-only graph answers symbol lookups that grep
already answered, and loses every "how does X work" question. Keep docs in.

This overrides the generic `/graphify <code-dir> --directed` line in
`CODING_RULES.md`, whose `# e.g. src/ app/ lib/` comment is what makes `src/`
look right here. It isn't.

Two things that make the wrong scope easy to hit:

- `graphify-out/` is gitignored, so the scan-root sidecar
  (`graphify-out/.graphify_root`) never travels with a clone — and it holds an
  absolute path, so it *cannot* be committed either. A fresh checkout has no
  memory of the scope; the first rebuild must pass `.` explicitly.
- Any `/graphify <path>` run overwrites that sidecar, so a single
  wrong-path invocation leaves it pointing at the wrong root and a later bare
  `graphify update` rescans only that subtree — reading every file outside it
  as deleted.

Before rebuilding, confirm the scope: group `graphify-out/graph.json` nodes by
the first path segment of their `source_file`. If you see `docs`, `tools` and
`build.py` alongside `src`, the graph is root-scoped — keep it that way.
