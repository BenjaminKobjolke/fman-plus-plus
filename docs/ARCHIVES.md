# Archives (7-Zip)

fman browses and edits `.zip`, `.7z` and `.tar` archives as if they were
folders. `.rar` archives also open like folders and can be browsed and copied
out of; RAR and compressed TAR archives are read-only, so changes inside them
are refused. The archive filesystems run 7-Zip through `core/fs/zip.py`,
`core/fs/rar.py` and `core/fs/compressed_tar.py`.

The bundled binary is `7z.exe` plus `7z.dll` on Windows and `7zz` on Mac and
Linux, under `src/main/resources/base/Plugins/Core/bin/<platform>/`. Arch uses
the system binary `/usr/bin/7za`. Each bundled platform binary has its own
`License.txt` beside it. The Mac and Linux binaries are downloaded and staged
by `tools/update_7zip.bat`; run that script before the next Mac or Linux build.

Long-running operations show a progress bar. On Windows that progress used to
cost more than the work itself.

## Why extraction used to be slow, and the bar never moved

7-Zip only prints progress when it believes it is talking to a terminal. To get
those lines, fman used to spawn `7z.exe` through a pseudo-terminal
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
   released builds had a pseudo-console with no console host: `7z.exe` died
   instantly with `STATUS_CONTROL_C_EXIT` (`0xC000013A`) and no output, and
   every extract-with-progress failed.

## What fman does now

7-Zip is started with **`-bsp1`**, which redirects its progress stream to
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

Unix keeps its own `pty.fork()`-based progress runner
(`Run7ZipViaPty`) and invokes its platform binary through that runner.

## 7-Zip 26 compatibility

7-Zip 26 adds fractional seconds to some `Modified` values in its technical
listing output; the filesystem parses the date and time portion so these
entries remain browseable. On Mac and Linux, 7-Zip 26 follows symlinks by
default and rejects the old p7zip `-l` switch, so fman omits that switch while
keeping the same follow-symlinks behavior.

The vendor script downloads the official Windows, Mac and Linux binaries,
places each binary and its license in the platform folder, removes the old
`7za` files, stages the changed binaries, and marks Mac/Linux `7zz` executable.
When changing `SEVEN_ZIP_VERSION` in `tools/update_7zip.bat`, also update the
version and its matching source URL in `src/main/resources/base/LICENSE`.
The shipped 7-Zip 26.00 source is published at
<https://www.7-zip.org/a/7z2600-src.7z>.

## Canceling

Canceling used to send `Ctrl+C` into the pseudo-terminal, which gave 7-Zip the
chance to tidy up after itself. Without a terminal, fman kills the process
instead — and a killed 7-Zip process leaves its work file behind.

While updating an existing archive, 7-Zip writes a sibling `<archive>.tmp` and
renames it when it is done. So after a canceled run, `remove_7zip_temp_archive()`
deletes that leftover. It only fires for commands that rewrite an archive in
place (`a`, `d`, `rn`, `u`), never for extraction, and a missing or locked
`.tmp` is not an error — a stray work file must not break canceling.

Covered by `core/tests/fs/test_zip_temp_archive.py`.

## Passwords

Copying a file out of an encrypted zip or 7z archive prompts for its password
when needed. fman keeps a successful password in memory until it closes; it is
never written to disk. A wrong password clears the remembered value, shows
"Wrong password.", and prompts again. Each attempt extracts into a fresh
temporary directory because 7-Zip can leave empty files behind after a failed
attempt. Only a successful extraction is moved to the destination.

7-Zip receives passwords through stdin so they do not appear in its command
line. For encrypted archive creation, fman uses the bare `-p` switch and sends
the password on stdin. For extraction, the bundled Windows 7-Zip 26.00 treats
bare `-p` as an empty password, so fman omits that switch and lets 7-Zip read
stdin. Password runs merge stderr into stdout because 7-Zip reports wrong
password errors there; fman identifies those messages and retries with a new
prompt.

The `Pack to archive with password` command asks for the password twice. Zip
archives use AES-256, which Windows Explorer's built-in zip support cannot
open; use 7-Zip File Manager or WinRAR. 7-Zip cannot create zip archives with
non-ASCII passwords, so fman refuses those and suggests `.7z`; 7z archives
accept non-ASCII passwords. The archive file names remain visible because
header encryption is not enabled. fman cannot browse 7z archives whose file
names are encrypted, or delete and rename entries inside an encrypted solid
7z archive.

## Compressed TAR archives

`.tar.xz`/`.txz`, `.tar.gz`/`.tgz`, `.tar.bz2`/`.tbz2`/`.tbz` and
`.tar.zst`/`.tzst` archives open as read-only folders. 7-Zip exposes only the
outer compressed file (or the inner `.tar`) for these formats, so fman first
unpacks that outer layer to a temporary copy and then browses the copy as a TAR.
The copy uses disk space equal to the uncompressed TAR until fman exits or the
archive changes. Zstandard browsing requires a 7-Zip build that supports zstd:
the bundled build does, while Arch's `/usr/bin/7za` may not.

## Code map

| Where | What |
|---|---|
| `core/fs/zip.py` → `_7zip` | Context manager around one 7-Zip run: picks the runner, exposes `stdout_lines`, raises `_7zipError` on a non-zero exit |
| `core/fs/zip.py` → `Popen7ZipWindows` | Plain run, no progress (listing, deleting, extraction) |
| `core/fs/zip.py` → `Popen7ZipWindowsWithProgress` | Adds `-bsp1`; used whenever a task shows a progress bar |
| `core/fs/zip.py` → `Run7ZipViaPty` | The Unix pseudo-terminal runner |
| `core/fs/zip.py` → `_7zipTaskWithProgress` | Reads the output, matches ` NN% `, updates the task's progress |
| `core/fs/zip.py` → `remove_7zip_temp_archive` | Deletes `<archive>.tmp` after a canceled update |
| `core/fs/read_only_archive.py` → `_ReadOnly7ZipFileSystem` | Shared refusal behavior for read-only archive filesystems |
| `core/fs/compressed_tar.py` → `CompressedTarFileSystem` | Decompresses compressed TAR wrappers into temporary copies for browsing |

## Running the tests

The archive tests are excluded from `run_core_tests.bat` (their filename does
not match `test*.py`) because they spawn 7-Zip for real:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\fman'; cmd /c '.\tools\run_zip_tests.bat'"
```

`remove_7zip_temp_archive` is pure and needs no binary, so its tests live in
`test_zip_temp_archive.py` and do run in the fast suite.
