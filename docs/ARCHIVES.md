# Archives (7-Zip)

fman browses and edits `.zip`, `.7z` and `.tar` archives as if they were
folders. Everything behind that — listing, extracting, packing, renaming inside
an archive — is the bundled `7za` binary
(`src/main/resources/base/Plugins/Core/bin/<platform>/`), driven by
`core/fs/zip.py`.

Long-running operations show a progress bar. On Windows that progress used to
cost more than the work itself.

## Why extraction used to be slow, and the bar never moved

7-Zip only prints progress when it believes it is talking to a terminal. To get
those lines, fman used to spawn `7za.exe` through a pseudo-terminal
([pywinpty](https://pypi.org/project/pywinpty/)) whenever a task wanted
progress. Three problems came with it:

1. **It was slow.** pywinpty 2.x and later default to the ConPTY backend.
   Measured on a 62 MB / 992-file zip: **9.8 s** through ConPTY versus **1.7 s**
   through a plain pipe — the pseudo-terminal, not 7-Zip, was the bottleneck.
2. **The progress bar never updated anyway.** ConPTY hands back terminal
   *chunks*, not lines: `'  0%'`, then `'\r    \r'` to erase it, plus ANSI
   escapes. The percentage matcher expects a line, so it almost never matched.
3. **It needed extra files next to the frozen app.** ConPTY is implemented by
   `conpty.dll`, which launches `OpenConsole.exe` from its own directory.
   PyInstaller bundles DLL dependencies but not that companion executable, so
   released builds had a pseudo-console with no console host: `7za.exe` died
   instantly with `STATUS_CONTROL_C_EXIT` (`0xC000013A`) and no output, and
   every extract-with-progress failed.

## What fman does now

`7za` is started with **`-bsp1`**, which redirects its progress stream to
stdout. No terminal is involved, so a plain `Popen` pipe is enough:

```
 12% 142 - exports\some-file.png
 26% 252 - exports\another-file.svg
```

Each line ends in a lone `\r`, which the `TextIOWrapper` around stdout turns
into a line break — so the same parser that reads 7-Zip's other output reads the
progress too.

Consequences:

- Extraction and packing run at full speed (~6x faster than the ConPTY path on
  the measurement above), and the progress bar updates while they run.
- **pywinpty is no longer a dependency.** It is gone from
  `pyproject.toml`, from the PyInstaller hidden imports in
  `src/build/settings/windows.json`, and the build no longer copies any winpty
  helper into the frozen output.
- The zip tests no longer spawn a real console, so the AV/EDR hang they used to
  risk is gone.

Unix keeps its own `pty.fork()`-based runner (`Run7ZipViaPty`). It is cheap
there, and the bundled p7zip builds are not all new enough to be trusted with
`-bsp1`.

## Canceling

Canceling used to send `Ctrl+C` into the pseudo-terminal, which gave 7-Zip the
chance to tidy up after itself. Without a terminal, fman kills the process
instead — and a killed `7za` leaves its work file behind.

While updating an existing archive, 7-Zip writes a sibling `<archive>.tmp` and
renames it when it is done. So after a canceled run, `remove_7zip_temp_archive()`
deletes that leftover. It only fires for commands that rewrite an archive in
place (`a`, `d`, `rn`, `u`), never for extraction, and a missing or locked
`.tmp` is not an error — a stray work file must not break canceling.

Covered by `core/tests/fs/test_zip_temp_archive.py`.

## Code map

| Where | What |
|---|---|
| `core/fs/zip.py` → `_7zip` | Context manager around one `7za` run: picks the runner, exposes `stdout_lines`, raises `_7zipError` on a non-zero exit |
| `core/fs/zip.py` → `Popen7ZipWindows` | Plain run, no progress (listing, deleting, extraction) |
| `core/fs/zip.py` → `Popen7ZipWindowsWithProgress` | Adds `-bsp1`; used whenever a task shows a progress bar |
| `core/fs/zip.py` → `Run7ZipViaPty` | The Unix pseudo-terminal runner |
| `core/fs/zip.py` → `_7zipTaskWithProgress` | Reads the output, matches ` NN% `, updates the task's progress |
| `core/fs/zip.py` → `remove_7zip_temp_archive` | Deletes `<archive>.tmp` after a canceled update |

## Running the tests

The archive tests are excluded from `run_core_tests.bat` (their filename does
not match `test*.py`) because they spawn `7za` for real:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_zip_tests.bat'"
```

`remove_7zip_temp_archive` is pure and needs no binary, so its tests live in
`test_zip_temp_archive.py` and do run in the fast suite.
