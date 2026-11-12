# Royi sync ledger

Which changes from the RoyiFileManager fork have been ported into this fork.
Maintained by the `royi-sync` skill (`.claude/skills/royi-sync/SKILL.md`).

Source: https://github.com/RoyiAvital/RoyiFileManager (local: `D:\GIT\GitHub\RoyiFileManager`)
Last reviewed: v0.20.4 (83f5d66)

The two repositories share no git history, so nothing can be merged or
cherry-picked — every row is a manual re-implementation. Rows follow the
bullets of Royi's `CHANGELOG.md`, newest version first.

Status: `pending` (not looked at yet), `ported`, `skipped` (with reason).
Notes starting with easy / adapt carry the triage of 2026-10-20 (todo #12159).

| Version | Change | Status | Note |
|---------|--------|--------|------|
| 0.20.4 | Explorer archive copy/paste and drag/drop | pending | easy — archive items enter panes through the normal copy flow |
| 0.20.4 | Archives nested in archive-named folders fail to open or copy | pending | easy — archive path recognition issue |
| 0.20.4 | Archives guide and plug-in API documentation | skipped | his docs |
| 0.20.3 | Backspace at a drive root opens and highlights that drive | ported | 2026-11-11 — `src/main/resources/base/Plugins/Core/core/commands/navigation.py` |
| 0.20.2 | Empty-space context menu creates a new file | ported | 2026-11-11 — `src/main/resources/base/Plugins/Core/Folder Context Menu (Windows).json`, `(Linux).json`, `(Mac).json`, `core/commands/new_file.py`; `CreateAndEditFile` alias rename not ported |
| 0.20.2 | Command Center updates settings file template with missing defaults | pending | |
| 0.20.2 | Batch File Renamer adds UUID, HASHID and SQIDS aliases | pending | |
| 0.20.1 | Find blocking processes | skipped | already implemented in `Plugins/ProcessPane` and `core/tests/commands/test_locking_processes.py` |
| 0.20.0 | File Attributes Editor plug-in | pending | |
| 0.20.0 | `fman.ui.show_quick_check_list` | pending | |
| 0.20.0 | `fman.fs.notify_file_changed(url)` | pending | |
| 0.19.3 | Application metadata moved to `src/AppMeta.json` | pending | |
| 0.19.3 | Archive writes use pipe-based progress and drop `pywinpty` | pending | |
| 0.19.3 | Faster folder listings without native parser | pending | |
| 0.19.3 | `fman.fs.iterdir` no longer caches names | pending | |
| 0.19.3 | Plug-in columns register as their own instance | pending | |
| 0.19.3 | Remove unused plug-in APIs | pending | |
| 0.19.3 | Remove inherited fman assets and state | pending | |
| 0.19.3 | Errors in UI callbacks no longer close the app | pending | |
| 0.19.3 | Quicksearch dialogs restore focus when closed | pending | |
| 0.19.3 | Update plug-in API documentation | pending | |
| 0.19.3 | Document `python build.py test-docs` | pending | |
| 0.19.2 | QuickView plays animated GIF, WebP and APNG | pending | |
| 0.19.2 | About window has an olive border | pending | |
| 0.19.2 | Cross-drive drag follows copy/move modifiers | pending | |
| 0.19.1 | Create missing user settings files from defaults | pending | |
| 0.19.1 | Bundle DirectorySize and QuickView defaults | pending | |
| 0.19.1 | Convert configuration filenames to YAML naming | pending | |
| 0.19.1 | Plug-in settings ship commented YAML defaults | pending | |
| 0.19.1 | About window replaces Zen command | pending | |
| 0.19.1 | Rename application metadata file to `AppMeta.json` | pending | |
| 0.19.1 | Cross-drive moves use their own progress and cancel | pending | |
| 0.19.1 | Reuse read buffer when copying many small files | pending | |
| 0.19.1 | Prepare status bar counts and sizes off the UI thread | pending | |
| 0.19.1 | Find Files counts results past table limit efficiently | pending | |
| 0.19.1 | QuickView table filters continue while typing | pending | |
| 0.19.1 | QuickView table reports format errors with DuckDB guidance | pending | |
| 0.19.1 | Remove unused Core AppSettings JSON | pending | |
| 0.19.1 | Cross-drive move preserves changed or canceled source | pending | |
| 0.19.1 | Recover from damaged saved window position | pending | |
| 0.19.1 | Favorites distinguish Unicode-equivalent folder names | pending | |
| 0.19.1 | Quit from Command Center no longer reports an error | pending | |
| 0.19.1 | QuickView table cache is removed on quit | pending | |
| 0.19.1 | Copying control characters from QuickView avoids PDF error | pending | |
| 0.19.1 | New folder reports invalid-name and read-only errors | pending | |
| 0.19.0 | Command Center groups commands by category | pending | |
| 0.19.0 | Plug-in commands and panes expose command categories | pending | |
| 0.19.0 | Toggle live refresh during file operations | pending | |
| 0.19.0 | Edit settings opens application settings | pending | |
| 0.19.0 | Add plug-in `load_settings` and `save_settings` APIs | pending | |
| 0.19.0 | User configuration supports YAML comments | pending | |
| 0.19.0 | Move application settings into AppSettings.yaml | pending | |
| 0.19.0 | Rename QuickView image commands | pending | |
| 0.19.0 | Widen QuickSearch lists | pending | |
| 0.19.0 | Remove legacy text editor launch mappings | pending | |
| 0.19.0 | Remove old Search Files settings keys | pending | |
| 0.19.0 | Concurrent settings saves preserve each other's changes | pending | |
| 0.19.0 | Elide long QuickSearch hints | pending | |
| 0.19.0 | Command Center handles case-expanding Unicode names | pending | |
| 0.19.0 | Document live refresh behavior | pending | |
| 0.19.0 | Document YAML settings APIs and comments | pending | |
| 0.18.1 | Properties no longer crashes on Windows | pending | |
| 0.18.1 | QuickView table sizes record-number column during loading | pending | |
| 0.18.0 | QuickView adds CSV and TSV Table View | pending | |
| 0.18.0 | Add QuickView table file and memory limit setting | pending | |
| 0.18.0 | Rename duplicate command in menus and Command Center | pending | |
| 0.18.0 | Add Copy item(s) name and path commands | pending | |
| 0.18.0 | Remove redundant `copy_paths_to_clipboard` command | pending | |
| 0.17.1 | Add Royi Text Editor preset | pending | |
| 0.17.1 | Shorten context menu copy name and path labels | pending | |
| 0.17.1 | Summarize Find Files traversal errors | pending | |
| 0.17.0 | Swap pane locations and add clipboard/link navigation | pending | |
| 0.17.0 | Keypad selection preview and same-extension selection | pending | invert and same-extension commands already exist; keypad `+` / `-` preview remains to review |
| 0.17.0 | Add Command Center synonyms | pending | |
| 0.17.0 | Show local available and total space in extended status | pending | |
| 0.17.0 | Add `DirectoryPane.get_location_info()` | pending | |
| 0.17.0 | Copy selected names as newline-separated text | pending | |
| 0.17.0 | Duplicate suggests available `name Copy N.ext` names | ported | 2026-11-06 — `core/commands/duplicate.py`, `core/commands/transfer.py`, `core/tests/commands/test_duplicate.py` |
| 0.17.0 | Coalesce Select and Deselect row updates | pending | |
| 0.16.4 | Create a duplicate file (alias Copy file here): Copy with the active pane as destination | ported | 2026-11-06 — `core/commands/duplicate.py`, `core/commands/transfer.py`, `core/tests/commands/test_duplicate.py`, Core command registration and platform context menus |
| 0.16.4 | Pack here (alias Compress here): Pack with the active pane as destination | ported | 2026-11-06 — `core/commands/pack.py`, `core/tests/commands/test_pack.py`, platform context menus |
| 0.16.4 | Default FileSystem.prepare_trash moves to trash instead of deleting | ported | 2026-10-20 — `src/main/python/fman/fs.py`, `test_mother_fs.py` |
| 0.16.4 | Delete in locations without a Recycle Bin refuses instead of deleting permanently | ported | 2026-10-20 — `core/commands/deletion.py`, `core/tests/commands/test_deletion.py`; message uses the platform's trash name |
| 0.16.4 | README Robocopy link | skipped | his docs |
| 0.16.3 | Batch File Renamer {c} / {d} random fields | pending | needs Batch File Renamer (0.15.0) |
| 0.16.3 | QuickBoard 900 x 600, compact numeric columns | pending | needs show_quick_board (0.15.0) |
| 0.16.3 | Batch File Renamer bundled in frozen builds | skipped | his packaging; renamer not ported |
| 0.16.3 | Copy file path menu entry shows the Copy-paths shortcut (F11) via `shortcut_command` | ported | 2026-10-14 — `src/main/python/fman/impl/plugins/context_menu.py`, `src/unittest/python/fman_unittest/impl/plugins/test_context_menu.py`, three File Context Menu JSON files |
| 0.16.2 | Single-item Copy file name / Copy file path in context menu and Command Center; Shift+F11 copies the name | ported | 2026-10-14 — `core/commands/clipboard.py`, `core/tests/commands/test_clipboard.py`, `core/tests/test_viewer_pane_commands.py`, `Key Bindings.json`, `docs/KEYBINDINGS.md` |
| 0.16.1 | Ecode preset for text editor / viewer setup | ported | 2026-10-14 — editor arguments only |
| 0.16.0 | Robocopy plug-in: Copy / Move with robocopy, wizard, progress, logs | ported | 2026-10-14 — Plugins/Robocopy/**, docs/ROBOCOPY.md, tools/run_robocopy_tests.bat, tools/run_robocopy_integration_tests.bat; fman.ui owner/resource replaced by a module lock, Job-Object process owner replaced by Popen |
| 0.15.0 | `fman.ui.show_quick_board` | pending | needs QuickTable (0.12.0) |
| 0.15.0 | Batch File Renamer plug-in | pending | needs `show_quick_board`, `rename_no_replace`, `reload(on_done=)` |
| 0.15.0 | `fman.fs.rename_no_replace` / `RenameResult` | pending | his local implementation is Windows-only |
| 0.15.0 | `DirectoryPane.reload(on_done=...)` | pending | his code reads snapshot-model internals (0.9.0) |
| 0.15.0 | Favorites Manager added / last opened / count | skipped | own external plug-in FMAN-Favorites |
| 0.15.0 | Copy/Move cancellable preparation before validation, missing nested destinations | pending | adapt — `transfer.py` creates the destination before the task; prepare before validation |
| 0.15.0 | Yes to all: skipped errors reported once at the end | ported | 2026-11-11 — `core/file_tree_gathering.py`, `core/fileoperations.py`, `core/skipped_errors.py`, `core/tests/test_fileoperations.py`, `core/tests/test_skipped_errors.py` |
| 0.15.0 | Public file selection batches Qt selection updates | ported | 2026-10-08 — `fman/impl/view/__init__.py`, `fman_unittest/impl/view/selection_test.py`, `tools/run_view_tests.bat` |
| 0.15.0 | QuickTable initial focus / visibility by source position | pending | needs QuickTable (0.12.0) |
| 0.15.0 | QuickList footer, third-press sort reset, frameless | pending | needs QuickList (0.3.0 / 0.14.0) |
| 0.15.0 | Fuzzy Find follows pane hidden-file visibility | pending | needs SearchFileFuzzy (0.2.0) |
| 0.15.0 | Saved JSON uses two-space indent and final newline | ported | 2026-10-08; `src/main/python/fman/impl/plugins/config.py`, `src/main/python/fman/impl/util/settings.py` |
| 0.15.0 | Copy to unavailable drive / share shows one clear error | ported | 2026-10-08; `core/fs/local/__init__.py`, `core/fileoperations.py` |
| 0.15.0 | Copy performance table, documentation | skipped | measurements / his docs |
| 0.14.0 | QuickView PDF preview | pending | needs QuickView (0.8.0); new dependency pypdfium2 |
| 0.14.0 | `fman.ui.show_quick_list` | pending | needs QuickList (0.3.0) |
| 0.14.0 | Favorites Manager on `show_quick_list` | skipped | own external plug-in FMAN-Favorites |
| 0.14.0 | QuickTable ASCII filter fast path | pending | needs QuickTable (0.12.0) |
| 0.14.0 | Removed Qt widget exports from `fman.ui` | skipped | exports never existed here |
| 0.14.0 | Reset window geometry stays cleared through shutdown | pending | needs Reset Window Geometry (0.1.0) |
| 0.14.0 | Exit access violation: skip interpreter teardown | ported | 2026-10-08; landed in `e54739b` (v0.13.1); `src/main/python/fman/main.py`, `src/unittest/python/fman_unittest/test_main.py` |
| 0.13.1 | Name sort keys in C (`_fsparser.natural_keys`) | pending | native binary; snapshot architecture (0.9.0) |
| 0.13.1 | Unchanged refresh skips re-sort / table reset | pending | snapshot architecture (0.9.0) |
| 0.13.1 | Projection worker yields every ~16 ms; smaller row map | pending | snapshot architecture (0.9.0) |
| 0.13.1 | Performance tables | skipped | no code |
| 0.13.0 | Native NTFS directory parser (`fsparser.c`) | pending | native binary, Windows-only; snapshot architecture (0.9.0) |
| 0.13.0 | Performance tables | skipped | no code |
| 0.12.0 | `show_table` reworked into `show_quick_table` (breaking) | pending | supersedes the 0.4.0 `show_table` row: port this shape, not the old API |
| 0.12.0 | Typed `QuickTableColumn`, header sort/filter icons, `truncated`, tab cells, cell menus | pending | part of QuickTable |
| 0.12.0 | Search Files Extended mode | pending | needs Search files (0.4.0) |
| 0.12.0 | Find Files / Search Files / Verify checksum result changes | pending | need 0.7.0 / 0.4.0 / 0.10.3 plug-ins |
| 0.12.0 | Natural name sorting moved to a shared host helper | pending | |
| 0.12.0 | Removed per-pane mode of Extended Status Bar | pending | needs extended status bar (0.2.0) |
| 0.12.0 | Documentation | skipped | his docs |
| 0.11.0 | Everything Search plug-in (Ctrl+E), database folder manager | pending | bundles Everything portable binary |
| 0.11.0 | Build auto-provisions hash-verified Everything portable files | pending | belongs to the plug-in above |
| 0.10.3 | ChecksumFiles plug-in (generate / verify checksum files) | pending | needs `show_table` (0.4.0), BLAKE3 dependency |
| 0.10.3 | `get_background_menu` callback in `fman.ui.show_table` | pending | needs `show_table` (0.4.0) |
| 0.10.3 | Performance retest report | skipped | measurement of his builds, no code |
| 0.10.2 | Faster readback of selected file lists (36x on 200k files) | pending | adapt — this fork reads selected rows per index; Royi's helper reads snapshot rows |
| 0.10.2 | Simplified clipboard, Explorer and Recycle Bin command handling | skipped | clipboard / Explorer / Recycle Bin handling is already split across Core commands here |
| 0.10.2 | QuickView Find field forwards modified Enter shortcuts | pending | needs QuickView (0.8.0 / 0.10.0) |
| 0.10.2 | Compare directories reports selected visible differences | pending | easy — `core/commands/external.py` compares names; count selected visible differences |
| 0.10.2 | Pack at drive root suggests `C.zip` instead of `C:.zip` | ported | 2026-10-03 — `core/commands/pack.py` (`_suggest_archive_name`), `core/tests/commands/test_pack.py` |
| 0.10.2 | Delete continuation prompts use the task dialog, explicit Yes default | ported | 2026-11-11 — `core/commands/deletion.py`, `core/tests/commands/test_deletion.py` |
| 0.10.1 | Removed macOS/Linux runtime branches | skipped | this fork stays cross-platform |
| 0.10.1 | Removed GitHub plug-in installer | skipped | this fork keeps it (`docs/INSTALL_PLUGINS.md`) |
| 0.10.1 | Removed telemetry / event history | pending | adapt — telemetry is sent by `impl/metrics.py`; tours read the metrics state, product decision needed |
| 0.10.1 | Removed legacy Column `get_str` / `get_sort_value` | skipped | only valid on snapshot architecture (0.9.0) |
| 0.10.1 | Renamed "Show processes" to "Show OS' processes" | pending | needs ProcessPane (0.6.0) |
| 0.10.1 | Less unknown-identity checking when reconciling listings | pending | snapshot architecture (0.9.0) |
| 0.10.1 | Arrow-key suggestions offer local bindings; removed "Other" feedback field | pending | easy — suggestions do not offer local bindings; remove the Other field |
| 0.10.1 | Drive-label lookup moved to the filesystem scanner | pending | snapshot architecture (0.9.0) |
| 0.10.1 | Optional date edits commit on Enter / focus loss | pending | needs Find files panel (0.7.0) |
| 0.10.1 | Documentation updates | skipped | his docs |
| 0.10.0 | QuickView previews text, Markdown and source code | pending | needs QuickView (0.8.0); this fork has own text viewer |
| 0.9.3 | Less redundant pane column sizing, icon-key and status checks | pending | |
| 0.9.3 | Find reuses name/path normalization, streams ranked candidates | pending | needs SearchFileFuzzy (0.2.0) |
| 0.9.3 | Command Center avoids repeated lowercase conversions | pending | easy — `core/commands/palette.py` lowercases per command |
| 0.9.3 | Performance report | skipped | no code |
| 0.9.2 | File operations no longer traverse junction targets; hardlink copies refused | pending | adapt — `core/fs/local/__init__.py` only checks `islink`; junction detection needs the reparse-point attribute |
| 0.9.2 | Staged copies, Windows overwrite preserves DACLs and streams | pending | adapt — copies write straight to destination; Windows-specific and risky |
| 0.9.2 | Atomic session/dialog saves, linked settings files refused | pending | easy — plug-in JSON save is atomic; `impl/util/settings.py` session save is not |
| 0.9.2 | Worker/process startup failures release capacity and clean up | pending | |
| 0.9.2 | Folder-access failures recover through navigation; UTF-8/BOM config | pending | easy — config reads in `impl/util/settings.py` and `impl/plugins/config.py` omit encoding |
| 0.9.2 | Natural sort handles long numeric runs and Unicode digits; Go To keeps offline history | pending | easy — `core/__init__.py` pads to six digits; Go To probes `isdir` on offline paths |
| 0.9.2 | Resource cache hits avoid allocation; unchanged sort prefs skip disk writes | pending | |
| 0.9.2 | `FMAN_VERSION` replaced by `APP_VERSION` | skipped | rebrand |
| 0.9.2 | About dialog shows product version and links | skipped | rebrand |
| 0.9.2 | Removed obsolete pre-snapshot row loading | skipped | snapshot architecture cleanup |
| 0.9.2 | Application identity derived from `app_name` | skipped | rebrand / packaging |
| 0.9.2 | Documentation and performance report | skipped | his docs, no code |
| 0.9.1 | QuickView "Copy Image" button | pending | needs QuickView (0.8.0) |
| 0.9.0 | Snapshot pane architecture (immutable snapshots, one virtual model) | pending | very large; breaks filesystem/column/filter API |
| 0.9.0 | Filter Bar projections off the Qt thread | pending | part of snapshot architecture |
| 0.9.0 | Lazy icons and cell text through bounded caches | pending | part of snapshot architecture |
| 0.9.0 | Performance test suite (`python build.py measure`) | pending | |
| 0.9.0 | Synthetic benchmark fixtures | pending | belongs to the suite above |
| 0.9.0 | Native Filter Bar / Find / QuickView benchmark workloads | pending | belongs to the suite above |
| 0.9.0 | Escape in search panels returns focus to last active pane | pending | needs search panels (0.4.0 / 0.7.0) |
| 0.9.0 | Archive panes include deeply implied directories | pending | easy — `core/fs/zip.py` adds missing parents but its `*/*/*/*` exclusion hides them three levels down |
| 0.8.1 | Nested plug-in settings merge recursively (upstream `f3e48d2`) | ported | `fman/impl/plugins/config.py`, `test_config.py` |
| 0.8.1 | Reuse Windows directory entries' hidden attributes | skipped | `core/commands/hidden_files.py` already reads cached `st_file_attributes` |
| 0.8.0 | Image QuickView (Ctrl+Q) | pending | this fork has own image viewer |
| 0.8.0 | `tinycss` replaced by `tinycss2` | pending | new dependency |
| 0.8.0 | No row-height recalculation on metadata updates in large folders | ported | 2026-10-05 — `fman/impl/view/__init__.py` (vertical header `Fixed`), `view/uniform_row_heights.py` (`setDefaultSectionSize`; also on icon size change, which is fork-only), `fman_unittest/impl/view/uniform_row_heights_test.py`; measured at 37k rows: 0.33 s -> 0 s of GUI thread per background-load commit |
| 0.8.0 | Qt tests use nonblocking completion notification | pending | may relate to the known test hang; needs his main-thread `QApplication` test runner (`QtIT.run`, `qt_runner`) first |
| 0.7.1 | File / folder comparator wizards, Compare files / folders | pending | easy — only name-only `CompareDirectories` exists; reuse the text-editor wizard pattern |
| 0.7.1 | Find Files cancel reports Stopped, not Error | pending | needs Find files panel (0.7.0) |
| 0.7.1 | Find Files counts "entries" rather than "files" | pending | needs Find files panel (0.7.0) |
| 0.7.0 | Find files with fd panel (Shift+F7) | pending | bundles fd binary, needs `show_panel` (0.4.0) |
| 0.7.0 | `fman.ui` dropdown, date/integer fields, section dividers | pending | needs `show_panel` (0.4.0) |
| 0.7.0 | EmEditor preset for text editor / viewer | ported | 2026-10-14 — editor arguments only |
| 0.7.0 | Command renames: Find files, Favorites manager, Search files, New file | pending | |
| 0.7.0 | Minimum window size 960 x 600 | pending | easy — `impl/widgets.py` does not set a minimum on `MainWindow` |
| 0.6.4 | CudaText preset arguments | ported | 2026-10-14 — editor arguments only |
| 0.6.3 | Notepad 4 preset; Notepad++ preset arguments | ported | 2026-10-14 — editor arguments only |
| 0.6.2 | Notepad 4 preset | ported | 2026-10-14 — editor arguments only |
| 0.6.1 | Modified date and size beneath fuzzy search results | pending | needs SearchFileFuzzy (0.2.0) |
| 0.6.0 | ProcessPane plug-in (process list, F8 terminate) | pending | easy — can use the public `FileSystem` / `Column` API, like Robocopy |
| 0.6.0 | Fuzzy search supports fzf extended query operators | pending | needs SearchFileFuzzy (0.2.0) |
| 0.5.1 | External text viewer / editor wizards (F3 / F4) | ported | 2026-10-14 — `core/text_editor.py`, `core/commands/editor.py`, editor tests, `docs/KEYBINDINGS.md`; editor only (F4 + Set text editor); F3 external viewer and Clear option skipped — F3 is this fork's own text viewer; settings keep the fork's Popen-mapping format |
| 0.5.1 | About shows product version | skipped | rebrand |
| 0.5.0 | Pane filter syntax (`?`, classes, anchors, negation) and matched/total counts | pending | easy — current matcher supports only `*`; count must fit this fork's status bar |
| 0.5.0 | Search File Content lists files by name when content pattern is empty | pending | needs Search files (0.4.0) |
| 0.5.0 | Content Glob matches anywhere in a line | pending | needs Search files (0.4.0) |
| 0.5.0 | Closing a Table after navigation leaves target file current | pending | needs `show_table` (0.4.0) |
| 0.5.0 | TextField labels show input tooltips | pending | needs `show_panel` (0.4.0) |
| 0.4.4 | Directory totals in the Size column (Ctrl+Shift+D) | pending | easy — no directory totals; upstream implementation is about 460 lines and fits this model |
| 0.4.4 | Column widths restored by name across optional-column changes | pending | easy — `impl/session.py` restores widths by position |
| 0.4.4 | Ignore queued pane-reload results after model shutdown | pending | easy — `impl/model/model.py` has no shutdown guard in `_on_files_reloaded` |
| 0.4.3 | Unpack archive command | pending | easy — no unpack command; check `docs/ARCHIVES.md` before adding it |
| 0.4.2 | Archive extraction progress and cancel | pending | easy — `core/fs/zip.py` has no extraction progress; reuse this fork's `-bsp1` task pattern |
| 0.4.2 | Move out of / between archives verifies before deleting source | ported | 2026-11-06 — `core/fs/move_by_copy.py`, `core/fs/zip.py`, `core/tests/fs/zip_test.py`; destination existence check, not content digest |
| 0.4.2 | Failed or canceled extraction cannot trigger source deletion | ported | 2026-11-06 — `core/fs/move_by_copy.py`, `core/fs/zip.py`, `core/tests/fs/zip_test.py`; destination existence check, not content digest |
| 0.4.2 | Archive-to-archive Move no longer deletes source before packing succeeds | ported | 2026-11-06 — `core/fs/move_by_copy.py`, `core/fs/zip.py`, `core/tests/fs/zip_test.py`; destination existence check, not content digest |
| 0.4.2 | Windows directory publication refuses late destination conflicts | pending | |
| 0.4.2 | Build retries transient 7-Zip download failures | skipped | his build pipeline |
| 0.4.1 | Command Palette pins three most recent commands | pending | this fork has own palette work |
| 0.4.1 | `load_json(..., preserve_on_reload=True)` | pending | easy — `impl/plugins/config.py` and public API do not support preserving the loaded value |
| 0.4.1 | Search File Content pane indicators | pending | needs Search files (0.4.0) |
| 0.4.0 | Search File Content with ripgrep (Alt+F7) | pending | bundles ripgrep binary |
| 0.4.0 | Table UI component `fman.ui.show_table` | pending | prerequisite for many later rows |
| 0.4.0 | Docked panel UI component `fman.ui.show_panel` | pending | prerequisite for many later rows |
| 0.4.0 | `DirectoryPane.on_path_changed` subscriptions | pending | |
| 0.4.0 | Fuzzy matching prefers contiguous matches | pending | easy — `core/quicksearch_matchers.py` matches leftmost characters without a contiguity preference |
| 0.4.0 | Test suite timing issue with misleading permission traceback | pending | |
| 0.3.1 | Calculate File Hash (Ctrl+H) and algorithm picker | pending | needs `OutputTextBox` |
| 0.3.1 | `fman.ui.OutputTextBox` | pending | |
| 0.3.1 | Startup status uses application version | skipped | rebrand |
| 0.3.0 | Vector SVG application icon | skipped | his branding |
| 0.3.0 | Reusable `fman.ui` components (QuickList, bottom panel, toggles, settings bindings) | pending | |
| 0.3.0 | Public host-owned UI construction, pane tool windows, shared matchers | pending | |
| 0.3.0 | Favorites Manager (Ctrl+B) | skipped | covered by own external plug-in FMAN-Favorites (README "Plugins") |
| 0.2.2 | Extended Status Bar fixes (64-bit summaries, background, Active marker) | pending | needs extended status bar (0.2.0) |
| 0.2.1 | ZIP tests generate their fixture, accept fractional 7-Zip timestamps | pending | |
| 0.2.1 | Windows archive operations decode Unicode 7-Zip output consistently | pending | |
| 0.2.1 | Release builds materialize LFS icon | skipped | his build pipeline |
| 0.2.0 | SearchFileFuzzy plug-in (current-folder and recursive fuzzy search) | pending | |
| 0.2.0 | Optional extended status bar (Ctrl+S) | pending | this fork has own status bar work (`docs/STATUSBAR.md`) |
| 0.2.0 | Sync Pane Location command | pending | easy — navigation only opens the folder under the cursor in the other pane |
| 0.2.0 | Favorites plug-in (Ctrl+B) | skipped | covered by own external plug-in FMAN-Favorites (README "Plugins") |
| 0.2.0 | Ctrl+N creates an empty file without opening an editor | ported | 2026-11-11 — `src/main/resources/base/Plugins/Core/Key Bindings.json`, `(Mac).json`, `core/commands/new_file.py`; `CreateAndEditFile` alias rename not ported |
| 0.2.0 | README, provenance metadata, release-build hardening | skipped | his repo housekeeping |
| 0.1.0 | Portable distribution, conda workflow, PyInstaller packaging, 7-Zip retrieval | skipped | his packaging |
| 0.1.0 | Rebrand, local `fbs_runtime`, removed non-Windows and licensing code | skipped | his fork identity |
| 0.1.0 | Windows tests that do not need symlink privileges | pending | |
| 0.1.0 | Faster sorting of large directories and pane resizing | pending | includes the later "painting failed after resize" fix |
| 0.1.0 | Faster natural name sorting | pending | |
| 0.1.0 | Larger local file copy buffer | pending | easy — `core/fs/local/transfers.py` uses 16 KiB; Royi uses 1 MiB |
| 0.1.0 | Skip unused Gnome icon provider detection on Windows | pending | |
| 0.1.0 | F1 opens searchable keyboard shortcut guide | pending | adapt — F1 opens web help; palette already shows shortcuts |
| 0.1.0 | 1280x800 default window, Reset Window Geometry command | pending | easy — first run maximizes; only `CenterWindow` exists; read `docs/bugs/WINDOW_RESIZE_BUG.md` first |
| 0.1.0 | Application context lifetime fix (native Qt startup crashes) | skipped | same lazy `_main_window` lifetime pattern is already used here |
| 0.1.0 | Worker / file-watcher / QApplication shutdown races in tests | ported | 2026-10-03 — `fman/impl/model/model.py` (`shutdown` never ran `_shutdown_async`), `worker.py`, `file_watcher.py`, `fman_integrationtest/test_qt.py`; effect on the known test hang not measured |
| 0.1.0 | `Worker.submit` forwards keyword arguments | ported | 2026-10-03 — `fman/impl/model/worker.py`, `fman_unittest/impl/model/test_worker.py` |
| 0.1.0 | `WorkItem.__eq__` compared tuples incorrectly | ported | 2026-10-03 — same files as the row above |
| 0.1.0 | "Sort value is not loaded" after changing sort column then relaxing filter | ported | 2026-10-03 — `fman/impl/model/model.py` (`sort`), `fman_unittest/impl/model/test_model.py` |
| 0.1.0 | Move over existing file duplicated its name in cached listing | ported | 2026-10-03 — `fman/impl/plugins/mother_fs.py` (`_add_to_parent`), `test_mother_fs.py` |
| 0.1.0 | Duplicate additions to lazy plug-in directory listings left stale entries | ported | 2026-10-03 — `mother_fs.py` (`CachedIterator._record`); same change as the row above |
| 0.1.0 | Frozen Qt dependency collection, locked-build detection, title bar icon | skipped | his packaging |
