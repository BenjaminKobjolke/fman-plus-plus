# Robocopy

Copy or move selected files and folders with Windows' native `robocopy.exe`. The
commands are available from the command palette (`Ctrl+Shift+P`) as **Copy with
robocopy** and **Move with robocopy**. They are Windows-only and hidden on macOS
and Linux. Normal F5/F6 behavior is unchanged. There are no default key bindings
or context-menu entries.

## Use

Select files or folders in the active pane; when nothing is selected, the
highlighted entry is used. Choose a Robocopy command, then the destination
prompt opens with the opposite pane's folder filled in and selected, like F5/F6.
Press Enter to accept it, or type another absolute drive or UNC folder path. The
destination receives each selected item by name, including empty subfolders.
Unselected siblings are left alone.

Only one operation can run at a time, including destination selection and cleanup.
Another invocation reports **“A Robocopy operation is already active.”** Cancel
kills the running `robocopy.exe`; completed and partial filesystem changes are
kept. If fman itself crashes during a transfer, `robocopy.exe` keeps running:
the plug-in does not use a Windows Job Object, as with 7-Zip today.

## Native behavior and limits

Robocopy's copy policies apply. Native exit codes 0–7 mean no reported copy
failure; 8 or higher is a failure. This does not prove that every selected item
was copied or moved. A canceled or failed operation can leave partial destination
files and a partially moved selection. There is no staging, rollback, undo, or
content verification. Move checks selected roots afterward and reports what
remains.

The plug-in copies data, attributes, and timestamps. Selected source links and
junctions are refused; nested source links are excluded. Destination junctions
can redirect writes, and overwriting a hard-linked destination can change its
other aliases. Use ordinary filesystem entries and absolute local-drive or UNC
destinations. Relative paths, wildcards, device namespaces, alternate-stream
input paths, self-transfers, and directory-into-itself transfers are refused.

The progress display is a busy indicator with elapsed time and the selected
items or current job; it is not byte progress. Jobs run sequentially, with
Robocopy's `/MT` providing native parallelism. Same-volume F6 can be faster
because it may rename instead of copying and deleting.

## Settings

Bundled defaults are in `Plugins/Robocopy/Robocopy.json`. Optional overrides can
be placed at `%APPDATA%\fman\Plugins\User\Settings\Robocopy.json` or
`Robocopy (Windows).json`, then loaded with **Reload plugins**. Unknown keys and
invalid types or ranges are rejected.

| Setting | Default | Effect |
| --- | --- | --- |
| `threads` | `8` | Integer 1–32; Robocopy `/MT` thread count. |
| `retries` | `1` | Integer 0–10; retries per failed native operation. |
| `retry_wait_seconds` | `1` | Integer 0–30; wait between retries. |
| `restartable` | `false` | Use `/Z` for restartable network transfers. |
| `unbuffered` | `false` | Use `/J`, intended mainly for large-file I/O. |
| `log_enabled` | `false` | Write a UTF-16 transfer log. |
| `open_log_on_finish` | `false` | Open the log after completion; requires logging. |
| `log_retention_count` | `20` | Integer 1–100; retain the current and newest completed logs. |

Logs are stored under `<DATA_DIRECTORY>\Local\Robocopy\Logs`. They include
paths, filenames, command arguments, native output, exit codes, and the outcome;
review a log before sharing it. Logging and automatic opening are disabled by
default.

## For developers

The plug-in modules divide work among `settings`, `paths`, `jobs`, `planner`,
`logs`, `windows`, `transfer`, and `__init__`. Run `tools\run_robocopy_tests.bat`
for unit tests. `tools\run_robocopy_integration_tests.bat` runs tests that spawn
the real Windows `robocopy.exe` from both `*integration_test.py` files and is
Windows-only.
