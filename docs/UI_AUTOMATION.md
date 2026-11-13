# Windows and macOS UI automation

`tools\fman_ui.bat` on Windows and `tools/fman_ui.sh` on macOS start a private
fman process and drive its Qt window over the local scripting API. They support
automated checks of the command palette, file rows, dialogs, and screenshots
without taking over the developer's desktop.

## Safety and limits

The driver always uses a separate profile under `%TEMP%\fman-ui\` on Windows
or `$TMPDIR/fman-ui/` on macOS and never attaches to the fman process in the
user's profile. The instance starts signed out of the fman account with its
own keyring entry, so it does not sync account plugins or settings. By default,
it creates two
fixture folders there with `visible.txt`, a Windows-hidden `hidden.txt`, a
`folder` subfolder, and a `[--brackets--]` subfolder containing `visible.txt`.
The generated left fixture also includes `video.mp4`, copied from the committed
`examples/left_pane/dummy.mp4`; the right fixture does not. Caller-provided
`--left` and `--right` folders are left untouched. `launch` includes a `build`
object in its JSON result and saved session with the checkout's `version`,
short `commit`, `dirty` status, `checkout_path`, and `python` executable.
They also include an `ages` folder with `age_0d_fresh.txt` (0.1 days old),
`age_2d.txt`, `age_10d.txt`, `age_45d.txt`, `age_200d.txt`,
`age_400d_old.txt`, and the Windows-hidden `age_10d_hidden.txt`.
Optional `--left` and `--right` arguments select caller
provided fixture folders. Use only disposable test data: commands can modify
the folders opened in the two panes. `close` removes the generated profile and
fixtures; `restart` keeps both for the same session. On Windows, `close` also removes Recycle Bin entries whose original paths
are inside this session folder; it leaves caller-provided folders and other
Recycle Bin entries alone, and the close result reports how many entries it
removed. On macOS, files moved to the Trash remain there. The `hidden.txt`
fixture is not hidden on macOS.

A session that receives no driver command for 30 minutes, or whose fman process
has exited, is closed by a watchdog started with that session. The next
`launch` also removes such old sessions. `close` is still required at the end
of every check.

All commands except `launch` and `close` read the session information written
to the platform's temporary `fman-ui/current.json`; the driver never reads the
user's normal fman profile.
The instance runs without user plugins and does not move or click the real
mouse. fman's own dialogs can be inspected and answered; operating-system
dialogs and global hotkeys cannot be driven. Screenshots of video viewer areas
are black.

## Fixtures for file-age shading and large folders

The files in `ages` receive modification times relative to the launch time, so
each launch recreates the same age spread. Use `close` and then `launch` to reset
the fixture, including a hidden attribute or profile setting changed during a
check; use `restart` to keep those changes and the same profile. `--large N` creates `N` empty files in a `large` folder in the left
fixture only; the maximum is 50000. It is opt-in so ordinary launches remain
quick.

`--core-settings` accepts a JSON object and writes it to the isolated profile's
Core `Core Settings.json` before fman starts. Supported age-shading settings
include `file_age_shading`, `file_age_scale` (`log` or `steps`),
`file_age_style` (`transparency`, `tint`, or `bold`), and
`file_age_full_days`. fman reads these settings once at startup, so launch a new
session to try a different style or scale. The theme changes live with the
`Select theme` palette command; compact view, hidden files, and shading can be
changed with their palette commands.

This example follows validation task #2070: compare the age fixtures in both
panes and try the view options, then scroll through a large folder.

```bat
tools\fman_ui.bat launch --large 5000 --core-settings "{\"file_age_shading\":true,\"file_age_style\":\"tint\",\"file_age_scale\":\"steps\"}"
tools\fman_ui.bat click --file ages --double --pane 0
tools\fman_ui.bat click --file ages --double --pane 1
tools\fman_ui.bat screenshot %TEMP%\fman-ages.png
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type compact
tools\fman_ui.bat keys Return
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type hidden
tools\fman_ui.bat keys Return
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type Toggle file age shading
tools\fman_ui.bat keys Return
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type Toggle file age shading
tools\fman_ui.bat keys Return
tools\fman_ui.bat click --file age_2d.txt --pane 0
tools\fman_ui.bat keys Down
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type Select theme
tools\fman_ui.bat keys Return
tools\fman_ui.bat click --file .. --pane 0
tools\fman_ui.bat click --file large --double --pane 0
tools\fman_ui.bat keys End
tools\fman_ui.bat keys Home
tools\fman_ui.bat keys PgDown
tools\fman_ui.bat screenshot %TEMP%\fman-large.png
tools\fman_ui.bat close
```

## Use by the tickets watcher

The tickets watcher's validation agent finds this driver through the
`desktop_ui_driver` key in `tools/tickets-watcher.json`, which names
`tools/fman_ui.bat` on Windows; `tools/fman_ui.sh` is the macOS command. Both
paths must stay real files inside
the checkout or the watcher ignores the key. Agents may use `--large`,
`--core-settings` and `restart` to check settings across a restart; `--large`
and `--core-settings` stay inside the temporary fixture and profile. They
never use `--left` or `--right`, so checks cannot touch folders outside
`%TEMP%\fman-ui\`. Agents always run `tools\fman_ui.bat close` at the end,
including when a check fails. Screenshots an agent wants to attach go under the
ticket's `attach/validation/` folder.

## Commands

Every command prints one JSON result. API failures print `{"error": "…"}` and
exit with a nonzero code.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat launch --left C:\scratch\left --right C:\scratch\right
tools\fman_ui.bat restart
tools\fman_ui.bat state
tools\fman_ui.bat commands
tools\fman_ui.bat dialog
tools\fman_ui.bat command reload --pane 0
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat viewer --pane 0
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type hidden
tools\fman_ui.bat click --file visible.txt --pane 0 --double
tools\fman_ui.bat click --x 250 --y 140 --right
tools\fman_ui.bat drag --x 300 --y 60 --to-x 240 --to-y 60
tools\fman_ui.bat screenshot %TEMP%\fman.png
tools\fman_ui.bat close
```

`command` accepts an optional JSON argument object before `--pane`, for example
`tools\fman_ui.bat command open_directory "{\"url\":\"file:///C:/\"}"`.
`click --file` accepts either a full fman URL or a bare file name; names resolve
against the selected pane's current folder. Input commands accept `--settle`
milliseconds (default 500) to wait for the UI after acting.

`drag` uses the same window coordinates as `click --x` and `click --y`. Find a
column header's right edge in a screenshot and start the drag there. Drags that
start on file rows are refused, so file drag-and-drop cannot start. Take another
screenshot to confirm the result.

When a command opens an fman dialog, its HTTP request stays open until the
dialog is answered and may time out in the driver. If a dialog is active, the
command prints `{"running": true, "dialog": ...}` so the check can inspect its
type, title, text and buttons. `dialog` reads the active dialog directly. Use
`keys Return` or `keys Escape` to answer it, then inspect the command result or
run `dialog` again:

```bat
tools\fman_ui.bat command move_to_trash --pane 0
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat dialog
```

`dialog` also reports visible non-modal progress dialogs. Their `text` is the
dialog label, and `progress` contains its current `value` and `maximum`.
`viewer --pane N` reads the mounted viewer in that pane. For video it reports
`loaded`, `paused`, `position` (seconds), and `duration` (seconds); before the
player starts, the last three values are `null`. Video areas remain black in
screenshots, so use this readout to check playback.

## Example: first-use video playback

This checks the video player's first-use download in a fresh profile. The
launch result identifies the checkout build. While `view_file` is waiting,
`dialog` shows download progress; poll `viewer` before and after playback starts
to see its position advance.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat click --file video.mp4 --pane 0
tools\fman_ui.bat command view_file --pane 0
tools\fman_ui.bat dialog
tools\fman_ui.bat viewer --pane 0
timeout /t 2 /nobreak >nul
tools\fman_ui.bat viewer --pane 0
tools\fman_ui.bat close
```

The download dialog may already be gone by the time `dialog` is run if the
download completed quickly. When the libmpv archive is unavailable, `dialog`
reports the failure alert instead. Always close the session when the check is
finished.

## macOS

Run `tools/fman_ui.sh` with the same commands and arguments as the Windows
batch file. Sessions and fixtures live under `$TMPDIR/fman-ui/`. The driver
starts fman and its watchdog in separate process sessions so they keep running
after the shell command exits. `keys Ctrl+…` sends the Command key. The
`hidden.txt` fixture is visible on macOS, and closing the driver does not remove
files from the Trash.

## Example: check Force copy and Force move

This follows validation task #2075. On Windows, select two fixture files in the
left pane, then check the copy result in the right pane. Run the copy again to
inspect the overwrite dialog, then move and undo a file:

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat click --file visible.txt --pane 0
tools\fman_ui.bat keys Ctrl+F5
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat keys Ctrl+F5
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat keys Ctrl+F6
tools\fman_ui.bat command undo --pane 0
tools\fman_ui.bat close
```

On macOS, confirm both commands are registered and searchable in the palette:

```sh
tools/fman_ui.sh launch
tools/fman_ui.sh commands
tools/fman_ui.sh keys Ctrl+Shift+P
tools/fman_ui.sh type Force
tools/fman_ui.sh screenshot "$TMPDIR/fman-force-transfer.png"
tools/fman_ui.sh keys Escape
tools/fman_ui.sh close
```

## Example: hide and unhide a file

This follows the core actions from validation task #1492. The command palette
searches for the hide command; both pane listings can then be checked without
reading pixels.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type hidden
tools\fman_ui.bat keys Return
tools\fman_ui.bat files --pane 0
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat screenshot %TEMP%\fman-hidden.png
attrib -h "%TEMP%\fman-ui\<session-id>\left\hidden.txt"
tools\fman_ui.bat close
```

The `dialog` command also reports the in-window palette or prompt. A screenshot
then shows the main window with that dialog over it (separate modal dialogs and
popups are still captured on their own). The fixture's hidden attribute is set
when `launch` creates it; the `attrib` line shows how to reset it if a check
toggled it. Run `close` even when the check fails so the process and temporary
session are removed.

Input prompts such as Copy, Move, Rename and New folder report
`type: "Prompt"`, the full message in `text`, and the current entry text in
`value`. For a single item, a Copy or Move message includes the source name and
a second line with the destination folder. Password prompts report `value` as
`null` so typed passwords are never exposed. This follows validation task
#2206:

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat state
tools\fman_ui.bat click --file folder --pane 0
tools\fman_ui.bat keys F5
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat keys F6
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat close
```

Compare each prompt's destination line with the right pane's folder in the
`state` result.

## Example: narrow a column

This follows validation task #2072. Sort by Size, capture the header, then drag
the Size/Modified boundary left until Size no longer fits beside its sort arrow.
Use the screenshot to adjust the coordinates if needed, then capture the compact
header layout.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat click --x 80 --y 56
tools\fman_ui.bat screenshot %TEMP%\fman-column-before.png
tools\fman_ui.bat drag --x 123 --y 56 --to-x 52 --to-y 56
tools\fman_ui.bat screenshot %TEMP%\fman-column-after.png
tools\fman_ui.bat close
```

## Example: undo a file from the Recycle Bin

This follows validation task #1493. After `move_to_trash` times out, inspect the
active fman confirmation and answer it with `Return`. Undo restores the file;
the `state` result shows its cursor and selection. A second Undo opens the
"Nothing to undo." message. Repeat the same actions for the file in the
bracketed fixture folder to check that its path is handled literally.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat click --file visible.txt --pane 0
tools\fman_ui.bat command move_to_trash --pane 0
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat files --pane 0
tools\fman_ui.bat command undo --pane 0
tools\fman_ui.bat files --pane 0
tools\fman_ui.bat state
tools\fman_ui.bat command undo --pane 0
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat click --file [--brackets--] --pane 0 --double
tools\fman_ui.bat click --file visible.txt --pane 0
tools\fman_ui.bat command move_to_trash --pane 0
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat command undo --pane 0
tools\fman_ui.bat files --pane 0
tools\fman_ui.bat state
tools\fman_ui.bat command undo --pane 0
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat close
```

`close` stops the isolated process, removes only trashed items from its own
session folder, and deletes that folder. Entries from the rest of the user's
Recycle Bin are preserved.

`restart` asks fman to quit gracefully and kills it after 15 seconds if needed.
It keeps the same profile, fixtures, port and token, so settings changed during
the check remain in place. Pane paths are restored from the state fman saved on
quit.

## Example: check pane location bars after restart

This follows validation task #2174. Hide the pane location bars from the command
palette, restart the same isolated session, and confirm the bars remain hidden:

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type Toggle pane location bars
tools\fman_ui.bat keys Return
tools\fman_ui.bat screenshot %TEMP%\fman-location-bars-hidden.png
tools\fman_ui.bat restart
tools\fman_ui.bat screenshot %TEMP%\fman-location-bars-after-restart.png
tools\fman_ui.bat state
tools\fman_ui.bat close
```
