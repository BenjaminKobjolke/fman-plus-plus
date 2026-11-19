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
Every `launch` and `restart` result also includes `startup_prompts` with
`demo_mode`, `update_check_scheduled`, and the current `dialog` value. The
`--demo <id>` option starts fman in automation demo mode and leaves consent
unanswered. Demo scripts send their own keys, which bypass the driver's pane
guards; use demo `1` (overview, which stays in the fixture panes) for the quiet
check and demo `25` (the usage-consent demo) as the positive control where
`dialog` reports the consent `MessageBox`. Demo mode needs the demos dependency:
run `uv sync --group demos`. The script plays its keys and fman quits about a
second after it ends, so later commands report that fman exited; still run
`close` to remove the isolated session.
The isolated profile pre-answers fman's combined error-report and
usage-statistics question, so it cannot swallow the first driver keys. Add
`launch --first-start` to leave those answers unset and omit the profile's
session file: the first start shows the welcome tutorial, `restart` shows the
consent question, and after choosing “No thanks” a second `restart` shows no
question. With this option, `dialog` reports tutorial steps as type `Overlay`,
with the speech bubble's plain text and button labels.
`launch` opens the private window at 1280×800;
`restart` keeps fman's saved geometry. Initial startup also records its actual
window size and screen usable area in the JSON result; a small display may add
`window_warning`. The user's normal fman window is not changed.
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

On Windows, opt in to a disposable network share with `launch --network-share`.
The driver creates a `share` fixture inside the session folder and exposes it
through the matching loopback admin-share UNC path (for example,
`\\localhost\D$\...\share`). The launch result includes its `network_share`
URL and `network_share_unc` path. `close` deletes the share with the session.
Only this share folder is added to the input fence; its parent and the rest of
the drive remain outside the fence. The `network://` overview remains refused.
Launch fails with the UNC path when Windows cannot reach the loopback admin
share, such as when admin shares are disabled. This option is available on
Windows only.

A session that receives no driver command for 30 minutes, or whose fman process
has exited, is closed by a watchdog started with that session. The next
`launch` also removes such old sessions. `close` is still required at the end
of every check.

Before `keys`, `type`, `click`, `drag` or `command`, the driver checks that
every pane's `state` path is inside this session's temporary folder or one of
its fixture folders. It refuses the action if any pane is outside those roots;
`null` paths count as outside. A standalone `keys Escape` is allowed so it can
close the folder tree and restore the pane. If another key is needed, use
`close` and `launch` to recover a clean session. Read-only commands and
`close`, `restart` and `launch` are not fenced.

The exact drive overview path `drives://` has a limited input allowlist:
`command move_cursor_up`, `move_cursor_down`, `move_cursor_home`,
`move_cursor_end`, `show_explorer_properties` and `go_back`, plus `keys` using
only `Up`, `Down`, `Home` or `End`. Other actions are refused. Drive paths such
as `drives://C:` remain outside the fixtures and are always refused. Opening
the overview with `command show_volumes` from a fixture is allowed.

Before `command`, the driver also checks for an open dialog. It refuses a
command while a prompt or message box is open and reports its type and text;
answer it with keys first. Non-modal progress dialogs and tutorial overlays do
not block commands. Keys, typing and clicks remain available to answer a
prompt, subject to the pane-path fence.

The folder tree displays ancestors above the fixture, including folders on the
drive. Its highlighted folder is the pane location reported by `state`, while
`files --pane N` lists the underlying file list. Use `--deep` to exercise the
tree on a disposable nested fixture instead of navigating to a real folder.

All commands except `launch` and `close` read the session information written
to the platform's temporary `fman-ui/current.json`; the driver never reads the
user's normal fman profile.
The instance runs without user plugins by default; for FTP panes, see
"FTP and SFTP panes: use the FTP plugin's driver" below. It does not move or
click the real mouse. `launch --drop-plugin` opts into a disposable test plugin
that claims external file drops. fman's own dialogs can be inspected and answered.
Native Windows
Properties windows can be listed, captured with a whole-screen screenshot and
closed, but cannot be clicked or otherwise driven. A whole-screen screenshot
draws fman's own windows and Properties windows over the desktop in their real
stacking order, even when other programs cover them; other programs' windows
remain as they appear on screen. The installer subcommand can inspect and
answer its Windows installer dialog. Other operating-system dialogs and global
hotkeys cannot be driven. Screenshots of video viewer areas are black.
With automation enabled, the isolated instance records web links instead of
opening a browser.

## Fixtures for file-age shading, large folders and archives

The files in `ages` receive modification times relative to the launch time, so
each launch recreates the same age spread. Use `close` and then `launch` to reset
the fixture, including a hidden attribute or profile setting changed during a
check; use `restart` to keep those changes and the same profile. `--large N` creates `N` empty files in a `large` folder in the left
fixture only; the maximum is 50000. It is opt-in so ordinary launches remain
quick.

`--previous-version` writes the supplied version into the isolated profile's
saved session, so startup shows the update message and its Changelog link.
`links` reads the recent web addresses opened by fman and the link addresses in
recent status messages. Status messages remain in this readout after they fade
from the status bar.

`--core-settings` accepts a JSON object and writes it to the isolated profile's
Core `Core Settings.json` before fman starts. Supported age-shading settings
include `file_age_shading`, `file_age_scale` (`log` or `steps`),
`file_age_style` (`transparency`, `tint`, or `bold`), and
`file_age_full_days`. fman reads these settings once at startup, so launch a new
session to try a different style or scale. The theme changes live with the
`Select theme` palette command; compact view, hidden files, and shading can be
changed with their palette commands.

`--deep N` creates a six-level `deep/level_1/.../level_6` folder tree in the
left fixture, with `N` empty `sibling_0000`-style folders at each level above
`level_6`. The maximum is 5000 siblings per level. It is opt-in; `launch` adds
the absolute `level_6` path as `deep` in its JSON result and saved session when
`N` is greater than zero. Caller-provided `--left` folders are not changed.

`--archive N` creates `archive.zip` in the left fixture with `N` small text
files spread across the root and a four-level folder chain. It also contains
`large_file.bin`, exactly 2 097 152 bytes of fixed content. The archive uses
`ZIP_STORED`, so the large file remains large on disk; the maximum is 50000
small files. It is opt-in, and `launch` reports the absolute archive path as
`archive` when `N` is greater than zero. Caller-provided `--left` folders are
not changed.

Open the archive, inspect its listing, then select the large file and start a
copy to the right pane:

```bat
tools\fman_ui.bat launch --archive 20000
tools\fman_ui.bat click --file archive.zip --double --pane 0
tools\fman_ui.bat files --pane 0
tools\fman_ui.bat click --file large_file.bin --pane 0
tools\fman_ui.bat keys F5
tools\fman_ui.bat dialog
```

This follows validation task #2227. Convert the `deep` path from the first
command's JSON result to a `file://` URL with forward slashes (for example,
`D:\\temp\\fman-ui\\session\\left\\deep` becomes
`file://D:/temp/fman-ui/session/left/deep`) and use it in the
`open_directory` argument. The tree opens on the deep fixture, so the following
check exercises its long chain and sibling folders without opening a real
drive folder:

```bat
tools\fman_ui.bat launch --deep 300
tools\fman_ui.bat command open_directory "{\"url\":\"file://D:/.../deep/level_6\"}" --pane 0
tools\fman_ui.bat command toggle_folder_tree --pane 0
tools\fman_ui.bat state
tools\fman_ui.bat screenshot %TEMP%\fman-deep-tree.png
tools\fman_ui.bat keys F7
tools\fman_ui.bat dialog
tools\fman_ui.bat command new_folder --pane 0
tools\fman_ui.bat keys Escape
tools\fman_ui.bat keys Home
tools\fman_ui.bat keys F7
tools\fman_ui.bat keys Escape
tools\fman_ui.bat state
tools\fman_ui.bat close
```

Confirm the second command is refused while the F7 prompt is open. After
`Home`, F7 should be refused if the pane is outside the session fixtures;
standalone Escape closes the tree and restores the fixture location. Always
close the session, including if a check fails.

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

## Example: Windows installer update with two windows (validation task #2454)

This check installs the existing `target\fmanSetup.exe` into a disposable
folder under `%TEMP%\fman-ui\installer`, starts two fman windows, and checks
the installer's locked-file timeout. Build the setup first with
`tools\build_windows_installer.bat` when it is missing.

The check writes per-user `HKCU` installer entries, the user Start-menu
shortcuts and the user `Path` value, then restores their saved values during
cleanup. It refuses to start when `HKCU\Software\fman` already exists, so a
per-user fman install cannot be redirected. The all-users installation stays
untouched. The temporary copy uses `portable.txt` and its own `Data` profile;
the setup runs with `__COMPAT_LAYER=RunAsInvoker` and `/CurrentUser`. The driver
never runs the temporary `uninstall.exe`. Always run `installer cleanup`, even
after a failed check, to stop the temporary processes, restore the snapshot and
remove the temporary install.

Run the Retry sequence first, then poll `installer state` until its
`installer.exit_code` is set:

```bat
tools\fman_ui.bat installer launch
tools\fman_ui.bat installer update
timeout /t 65 /nobreak >nul
tools\fman_ui.bat installer state
tools\fman_ui.bat installer close-window --index 0
tools\fman_ui.bat installer answer retry
tools\fman_ui.bat installer state
tools\fman_ui.bat installer cleanup
tools\fman_ui.bat installer launch
tools\fman_ui.bat installer update
timeout /t 65 /nobreak >nul
tools\fman_ui.bat installer answer cancel
tools\fman_ui.bat installer state
tools\fman_ui.bat installer cleanup
```

After about 60 seconds, `state.message_box.text` should report that fman is
still running and cannot be updated, with `topmost: true`. After Retry, poll
`installer state` until `exit_code: 0`, confirm
`sentinel_present: false`, and find a fman process with
`started_after_update: true`. After Cancel, confirm `exit_code: 2`,
`sentinel_present: true`, the same installed version, and a process with
`started_after_update: true`.

## Use by the tickets watcher

The tickets watcher's validation agent finds this driver through the
`desktop_ui_driver` key in `tools/tickets-watcher.json`, which names
`tools/fman_ui.bat` on Windows; `tools/fman_ui.sh` is the macOS command. Both
paths must stay real files inside
the checkout or the watcher ignores the key. Agents may use `--large`, `--deep`,
`--archive`, `--network-share`, `--core-settings`, `--drop-plugin`, `drop` and
`restart` to
check settings across a restart; these options stay inside the temporary fixture
and profile. Agents may use the `installer` actions for the Windows installer
check and must always run `installer cleanup`. The driver refuses input and
commands when a pane leaves the session fixtures. `drop` also accepts only
existing source files inside the
session folder, never files from caller-provided pane folders. Agents always run
`tools\fman_ui.bat close` at the end,
including when a check fails. Screenshots an agent wants to attach go under the
ticket's `attach/validation/` folder. Agents may also use `--demo` to inspect
startup prompts.

## FTP and SFTP panes: use the FTP plugin's driver

fman's driver never loads user plugins. For checks of FTP or SFTP panes or FTP
plugin commands, use `%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat`,
documented in that plugin's `docs/FTP_UI_DRIVER.md`. It starts its own isolated
fman with the working-tree plugin and loopback FTP/SFTP fixture servers, forwards
fman's generic driver commands, and has its own `restart` that keeps the profile
and fixtures. Always run `close` at the end.

This sequence follows validation task #2497: hide the Permissions column, restart
fman, reopen the FTP fixture and inspect the screenshot, then show the column
again and close the session.

```bat
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" launch --delay 0
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" command open_directory "{\"url\":\"ftp://ftp-fixture/\"}" --pane 1
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" command toggle_ftp_permissions_column "{}" --pane 1
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" screenshot "%TEMP%\ftp-perm-hidden.png"
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" restart
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" command open_directory "{\"url\":\"ftp://ftp-fixture/\"}" --pane 1
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" screenshot "%TEMP%\ftp-perm-after-restart.png"
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" command toggle_ftp_permissions_column "{}" --pane 1
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" screenshot "%TEMP%\ftp-perm-shown.png"
call "%APPDATA%\fman\Plugins\User\FMAN_FTPClient\tools\ftp_ui_driver.bat" close
```

## Example: pack archives on a network share (validation task #2431)

The share fixture is reachable through fman's Network filesystem. The example
checks Pack, Pack here and password-protected Pack, then copies a file out of
each archive to inspect its contents. Replace the placeholder with the
`network_share` URL from the launch result:

```bat
tools\fman_ui.bat launch --network-share
tools\fman_ui.bat command open_directory "{\"url\":\"<network_share from launch>\"}" --pane 1
tools\fman_ui.bat state
tools\fman_ui.bat click --file visible.txt --pane 0
tools\fman_ui.bat command pack --pane 0
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat click --file <zip> --double --pane 1
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat keys Backspace
tools\fman_ui.bat click --file visible.txt --pane 1
tools\fman_ui.bat command pack_here --pane 1
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat click --file visible.txt --pane 0
tools\fman_ui.bat command pack_with_password --pane 0
tools\fman_ui.bat type <password>
tools\fman_ui.bat keys Return
tools\fman_ui.bat type <password>
tools\fman_ui.bat keys Return
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat restart
tools\fman_ui.bat command open_directory "{\"url\":\"<network_share from launch>\"}" --pane 1
tools\fman_ui.bat click --file <password-zip> --double --pane 1
tools\fman_ui.bat click --file visible.txt --pane 1
tools\fman_ui.bat command copy --pane 1
tools\fman_ui.bat keys Ctrl+A
tools\fman_ui.bat type copied.txt
tools\fman_ui.bat keys Return
tools\fman_ui.bat dialog
tools\fman_ui.bat type <password>
tools\fman_ui.bat keys Return
tools\fman_ui.bat files --pane 0
tools\fman_ui.bat close
```

In `state`, pane 1 should show a `file:////localhost/...` path. Choose the
generated ZIP name from `files` for each archive placeholder. Pack here asks
whether to update the existing `visible.zip`; answer Yes with `Return`. After
password-protected Pack, restart fman before checking extraction because fman
keeps a successful password in memory until it closes. Opening the protected
ZIP lists its filenames without a password; copy `visible.txt` out to
`copied.txt` to trigger the password prompt. `dialog` should report
`value: null`; after entering the password, `files --pane 0` should show
`copied.txt`.

## Example: demo-mode startup prompts (validation task #2319)

Demo `1` should report `demo_mode: true`, `update_check_scheduled: false`, and
`dialog: null`. A plain launch is the comparison and should report
`update_check_scheduled: true`. Demo `25` is the positive control: its
`startup_prompts.dialog` should contain the consent `MessageBox`.

```bat
tools\fman_ui.bat launch --demo 1
tools\fman_ui.bat close
tools\fman_ui.bat launch
tools\fman_ui.bat close
```

The driver starts fman outside the calling shell's job, so sandboxed agents can
run each command in its own shell call. When a connection is refused, the error
reports whether fman exited, along with the session id and the tail of its log.

## Example: check window and taskbar titles

The `native-windows` readout includes `window_title`, the title set on fman's
main Qt window, and `taskbar_title`, the caption Windows shows on its taskbar
button. `taskbar_title` is Windows-only and `null` on other platforms.

This checks the title with both fixture folders, with only the left folder
shown, and with both folders restored:

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat native-windows
tools\fman_ui.bat command show_only_active_pane --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat command show_all_panes --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat close
```

The first and last readouts name both fixture folders; the middle readout names
only the left folder.

## Example: check Properties window placement (validation task #2360)

The native Properties readout reports each window's rectangle and screen index,
the fman window and pane rectangles, and each selected cursor row. Compare the
Properties window top with the cursor-row bottom, confirm successive windows
are offset by 30 pixels, and check that each rectangle stays inside the screen's
available area and has the same screen index as fman. `screenshot --screen`
draws fman's own windows and Properties windows over the desktop in their real
stacking order, even when other programs cover them; other programs' windows
remain as they appear on screen. Close each Properties window with
`close-native-windows` after capturing it.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat command show_explorer_properties --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat screenshot --screen %TEMP%\fman-properties-single.png
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat command toggle_selection --pane 0
tools\fman_ui.bat command move_cursor_down --pane 0
tools\fman_ui.bat command toggle_selection --pane 0
tools\fman_ui.bat command move_cursor_down --pane 0
tools\fman_ui.bat command toggle_selection --pane 0
tools\fman_ui.bat command show_explorer_properties --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat screenshot --screen %TEMP%\fman-properties-three.png
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat command open_directory "{\"url\":\"file://.../folder\"}" --pane 0
tools\fman_ui.bat command show_explorer_properties --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat screenshot --screen %TEMP%\fman-properties-empty.png
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat command show_volumes --pane 0
tools\fman_ui.bat command move_cursor_down --pane 0
tools\fman_ui.bat command show_explorer_properties --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat screenshot --screen %TEMP%\fman-properties-drive.png
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat command go_back --pane 0
tools\fman_ui.bat command show_explorer_properties --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat window --y <available-y-plus-height-minus-window-height>
tools\fman_ui.bat command move_cursor_end --pane 0
tools\fman_ui.bat screenshot --screen %TEMP%\fman-properties-bottom.png
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat click --file visible.txt --pane 0
tools\fman_ui.bat command view_file --pane 0
tools\fman_ui.bat command show_explorer_properties --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat screenshot --screen %TEMP%\fman-properties-viewer.png
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat window --screen 1
tools\fman_ui.bat command show_explorer_properties --pane 0
tools\fman_ui.bat native-windows
tools\fman_ui.bat screenshot --screen %TEMP%\fman-properties-screen-2.png
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat close
```

For the three-file case, toggle the current file, move down and toggle twice;
the readout should show three
Properties windows. For the bottom-edge case, use the screen's
`available_geometry` from `native-windows` to calculate the `--y` value so the
fman window bottom meets the available bottom using its actual height from the
readout, then move the cursor to the end.
`window --screen 1` returns an error saying how many screens are available; on
a one-screen machine mark this case not checkable. To check it, add a second
physical or virtual display in Windows Display settings. The driver never
installs a virtual display.

## Commands

Every command prints one JSON result. API failures print `{"error": "…"}` and
exit with a nonzero code.

Before saving a screenshot, the driver reads the PNG's actual dimensions. If
either dimension is below the current minimum, it resizes the window and
captures once more. The minimum is 1280×768 unless a smaller window size was
requested with `window`. `screenshot --screen` captures the entire display and
skips the resize retry. A second undersized window image fails without writing the file, with a message
such as `Screenshot is 1000x700, below the 1280x768 minimum; the usable screen
area is 1000x700.` Successful screenshot results include `width` and `height`.
The `window` command accepts integer `width` and `height` values from 200
through 10000, reports the actual size, and keeps later screenshots at that
size for the main window. A screenshot minimum is reduced to the requested
width or height when it is below 1280×768. Popups are captured on their own at
their natural dimensions. The private automation API exposes the resize operation as
`POST /v1/window`, which returns the actual size and usable screen area; it is
unavailable unless automation is enabled for that isolated profile.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat launch --left C:\scratch\left --right C:\scratch\right
tools\fman_ui.bat restart
tools\fman_ui.bat state
tools\fman_ui.bat commands
tools\fman_ui.bat dialog
tools\fman_ui.bat links
tools\fman_ui.bat native-windows
tools\fman_ui.bat close-native-windows
tools\fman_ui.bat command reload --pane 0
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat viewer --pane 0
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type hidden
tools\fman_ui.bat click --file visible.txt --pane 0 --double
tools\fman_ui.bat click --x 250 --y 140 --right
tools\fman_ui.bat drag --x 300 --y 60 --to-x 240 --to-y 60
tools\fman_ui.bat drop --file <drop_source path from launch> --copy
tools\fman_ui.bat hover --x 400 --y 60
tools\fman_ui.bat window --width 800 --height 600
tools\fman_ui.bat window --y 200
tools\fman_ui.bat window --screen 1
tools\fman_ui.bat screenshot %TEMP%\fman.png
tools\fman_ui.bat screenshot --screen %TEMP%\fman-screen.png
tools\fman_ui.bat close
```

`hover` uses the same window coordinates as `click --x/--y`. It reports the
tooltip text because tooltips are separate windows and do not appear in the
screenshot. The hover highlight remains until another mouse event. `window`
reports the actual dimensions; later main-window screenshots keep the requested
size. Popup screenshots use the popup's natural dimensions.

### Example: check long-path hover and shortening (validation task #2366)

These coordinates fit the 800×600 window. Adjust them to the screenshot if your
layout differs. The first hover's `tooltip` should be the full path. The
screenshots show the ellipsis highlight, menu-item highlight, and shortened
path:

```bat
tools\fman_ui.bat launch --deep 6
tools\fman_ui.bat click --file deep --double --pane 0
tools\fman_ui.bat click --file level_1 --double --pane 0
tools\fman_ui.bat click --file level_2 --double --pane 0
tools\fman_ui.bat click --file level_3 --double --pane 0
tools\fman_ui.bat click --file level_4 --double --pane 0
tools\fman_ui.bat click --file level_5 --double --pane 0
tools\fman_ui.bat click --file level_6 --double --pane 0
tools\fman_ui.bat window --width 800 --height 600
tools\fman_ui.bat screenshot %TEMP%\fman-path-bar.png
tools\fman_ui.bat hover --x 180 --y 10
tools\fman_ui.bat hover --x 85 --y 10
tools\fman_ui.bat screenshot %TEMP%\fman-ellipsis-hover.png
tools\fman_ui.bat click --x 85 --y 10
tools\fman_ui.bat hover --x 70 --y 48
tools\fman_ui.bat screenshot %TEMP%\fman-hidden-folders-menu.png
tools\fman_ui.bat keys Escape
tools\fman_ui.bat close
```

The folder clicks stay inside the generated fixture. The coordinates target the
path-bar text and ellipsis, then a menu item in the popup.

### Example: check Help and Changelog links (validation task #2302)

```bat
tools\fman_ui.bat launch --previous-version 1.0.0
tools\fman_ui.bat links
tools\fman_ui.bat command help --pane 0
tools\fman_ui.bat links
tools\fman_ui.bat close
```

The first `links` result shows the `Updated to v…` message and its Changelog
address in `status_messages[].links`. The message fades from the status bar
after 5 seconds but remains in the readout. After `help`, `opened_urls` ends
with the Help address; no browser is opened by the isolated instance.
If a startup message box prevents `command help`, dismiss it with
`tools\fman_ui.bat keys Escape` and retry the Help command.

`command` accepts an optional JSON argument object before `--pane`, for example
`tools\fman_ui.bat command open_directory "{\"url\":\"file:///C:/\"}"`.
`click --file` accepts either a full fman URL or a bare file name; names resolve
against the selected pane's current folder. While the folder tree or a viewer is
mounted on that pane, `click --file` answers 409 because the file list is hidden;
pane commands then act on the tree's highlighted folder. Input commands accept
`--settle` milliseconds (default 500) to wait for the UI after acting.

`drag` uses the same window coordinates as `click --x` and `click --y`. Find a
column header's right edge in a screenshot and start the drag there. Drags that
start on file rows are refused to protect internal file-list drags. To test an
external file drop, use `drop` as shown below.

### Example: drop an external file (validation task #2447)

`launch` creates a disposable `drop_source/dropped.txt` outside both pane
folders and returns its path as `drop_source`. Pass that path to `drop`; the
driver refuses sources outside its session folder. Without the test plugin, a
Core copy or move prompt may appear. `dialog` shows that prompt, and `keys
Return` confirms it. A copy leaves the source in `drop_source`; the file appears
in pane 1 (or inside `folder` when `--onto folder` is used). A move also puts
the file in pane 1 and removes it from `drop_source`.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat drop --file "<drop_source path from launch>" --copy
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat close

tools\fman_ui.bat launch
tools\fman_ui.bat drop --file "<drop_source path from launch>" --move --onto folder
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Return
tools\fman_ui.bat click --file folder --pane 1 --double
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat close
```

The optional plugin claims the drop before Core handles it. It writes
`claimed_drop.txt` into the destination with the dropped names and copy/move
flag; pane 1 has that note but no `dropped.txt`, and `dialog` remains `null`.

```bat
tools\fman_ui.bat launch --drop-plugin
tools\fman_ui.bat drop --file "<drop_source path from launch>" --copy
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat dialog
tools\fman_ui.bat close
```

`hover --x N --y N` moves over the widget at those window coordinates and
returns its type and visible tooltip. The mouse move remains in place so the
next screenshot can show a hover highlight. `window --width N --height N`
resizes the isolated fman window and reports its actual dimensions and usable
screen area. Values from 200 through 10000 are accepted; main-window screenshots
keep that requested size, including widths below the usual minimum. When a
popup is active, the screenshot captures the popup on its own at its natural
dimensions.

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

## Example: first-start tutorial and consent

Use `--first-start` to verify the first-start flow. The welcome overlay's No
button responds to `Alt+N`; the consent question's “No thanks” button responds
to three Tabs followed by Return on the Windows driver:

```bat
tools\fman_ui.bat launch --first-start
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Alt+N
tools\fman_ui.bat restart
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Tab Tab Tab Return
tools\fman_ui.bat restart
tools\fman_ui.bat dialog
tools\fman_ui.bat close
```

The first `dialog` result is an `Overlay` with the welcome text and its No and
Yes buttons. The next `dialog` result is the consent `MessageBox`; after
choosing “No thanks”, the final result is `null`.

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

From Git Bash, a lone `/` argument becomes a path. Send it with `type /` or
prefix the command with `MSYS_NO_PATHCONV=1`.

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

The `dialog` command reports the in-window palette and prompts, including their
visible text and `font_sizes`. Quicksearch readouts use `title`, `value`, and
`footer`; prompts use `title`, `value`, and `detail`. Missing or hidden labels
have a `null` font size. A screenshot shows the main window with that dialog
over it (separate modal dialogs and popups are still captured on their own).
The fixture's hidden attribute is set when `launch` creates it; the `attrib`
line shows how to reset it if a check toggled it. Run `close` even when the
check fails so the process and temporary session are removed.

Rename is not a prompt: F2 and Shift+F6 edit the selected name inline. While
that editor is open, `dialog` reports `type: "RenameEditor"` and the edited
name in `value`; `command` is refused until Return or Escape closes the editor.
Copy, Move and New folder are prompts and report `type: "Prompt"`, the full
message in `text`, and the current entry text in `value`. For a single item, a
Copy or Move message includes the source name and a second line with the
destination folder. Password prompts report `value` as `null` so typed
passwords are never exposed. This follows validation task #2206:

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

## Example: palette text sizes across themes and zoom (validation task #2273)

The first dialog readout should be `null`. The palette readouts include its
title, query, and hint sizes; confirm `title > value > footer` in Dark and Light
themes before and after changing the pane font. New folder is a prompt, while
Rename is an inline editor:

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat dialog
tools\fman_ui.bat screenshot %TEMP%\fman-palette-dark.png
tools\fman_ui.bat keys Escape
tools\fman_ui.bat command increase_pane_font_size --pane 0
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type Select theme
tools\fman_ui.bat keys Return
tools\fman_ui.bat type Light
tools\fman_ui.bat keys Return
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat dialog
tools\fman_ui.bat screenshot %TEMP%\fman-palette-light.png
tools\fman_ui.bat keys Escape
tools\fman_ui.bat click --file visible.txt --pane 0
tools\fman_ui.bat keys F7
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat keys F2
tools\fman_ui.bat dialog
tools\fman_ui.bat keys Escape
tools\fman_ui.bat close
```

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
