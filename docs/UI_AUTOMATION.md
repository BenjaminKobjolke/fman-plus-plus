# Windows UI automation

`tools\fman_ui.bat` starts a private fman process and drives its Qt window over
the local scripting API. It is intended for automated checks that need to see
the command palette, file rows, clicks, or a screenshot without taking over the
developer's desktop.

## Safety and limits

The driver always uses a separate profile under `%TEMP%\fman-ui\` and never
attaches to the fman process in the user's profile. By default, it creates two
fixture folders there with `visible.txt`, a Windows-hidden `hidden.txt`, and a
`folder` subfolder. Optional `--left` and `--right` arguments select caller
provided fixture folders. Use only disposable test data: commands can modify
the folders opened in the two panes. The generated profile and fixtures are
removed by `close`.

All commands except `launch` and `close` read the session information written
to `%TEMP%\fman-ui\current.json`; the driver never reads `%APPDATA%\fman`.
The instance runs without user plugins and does not move or click the real
mouse. Native Windows dialogs and global hotkeys cannot be driven. Screenshots
of video viewer areas are black.

## Use by the tickets watcher

The tickets watcher's validation agent finds this driver through the
`desktop_ui_driver` key in `tools/tickets-watcher.json`, which names
`tools/fman_ui.bat` and this document. Both paths must stay real files inside
the checkout or the watcher ignores the key. Agents use only the default
fixtures, never `--left` or `--right`, so checks cannot touch folders outside
`%TEMP%\fman-ui\`. Agents always run `tools\fman_ui.bat close` at the end,
including when a check fails. Screenshots an agent wants to attach go under the
ticket's `attach/validation/` folder.

## Commands

Every command prints one JSON result. API failures print `{"error": "…"}` and
exit with a nonzero code.

```bat
tools\fman_ui.bat launch
tools\fman_ui.bat launch --left C:\scratch\left --right C:\scratch\right
tools\fman_ui.bat state
tools\fman_ui.bat commands
tools\fman_ui.bat command reload --pane 0
tools\fman_ui.bat files --pane 1
tools\fman_ui.bat keys Ctrl+Shift+P
tools\fman_ui.bat type hidden
tools\fman_ui.bat click --file visible.txt --pane 0 --double
tools\fman_ui.bat click --x 250 --y 140 --right
tools\fman_ui.bat screenshot %TEMP%\fman.png
tools\fman_ui.bat close
```

`command` accepts an optional JSON argument object before `--pane`, for example
`tools\fman_ui.bat command open_directory "{\"url\":\"file:///C:/\"}"`.
`click --file` accepts either a full fman URL or a bare file name; names resolve
against the selected pane's current folder. Input commands accept `--settle`
milliseconds (default 500) to wait for the UI after acting.

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

The screenshot is the current main window (or the active modal or popup). The
fixture's hidden attribute is set when `launch` creates it; the `attrib` line
shows how to reset it if a check toggled it. Run `close` even when the check
fails so the process and temporary session are removed.
