# System tray

On Windows, fman can stay running in the notification area (system tray) when
its window is hidden. Use the command palette (`Ctrl+Shift+P`) to find the tray
commands. Closing the window still quits fman; minimizing and hiding it are
separate actions.

## Tray commands

| Command | What it does |
|---|---|
| **Minimize to system tray** | Hides fman and shows its tray icon. Selecting the icon restores the window. |
| **Toggle minimize to tray** | Makes the window's minimize button hide fman to the tray. The tray icon stays visible while this is on. |
| **Minimize to taskbar** | Minimizes the window as usual, leaving it on the taskbar. |
| **Toggle start with Windows** | In an installed build, starts fman hidden in the tray when you sign in. |

The tray icon menu has **Show** and **Quit**. Quit uses fman's normal exit path,
which saves the session. If minimize-to-tray is off, the icon appears only while
the window is hidden in the tray. When minimize-to-tray is on, it stays visible
while fman runs.

## Settings

The settings are in `Local/Settings.json` in fman's data directory. They are
optional and default off:

| Key | Default | Effect |
|---|---|---|
| `minimize_to_tray` | `false` | The window's minimize button hides fman in the tray. |
| `global_hotkey` | unset | A Windows-wide key combination that toggles fman between hidden and shown. |
| `start_with_windows` | `false` | Starts fman hidden in the tray at Windows sign-in. |

For example, add `"global_hotkey": "Ctrl+Alt+F"` to set the hotkey. Restart
fman after changing it. The key is not reserved until you set one. If another
program already uses it, fman reports that and continues without the hotkey.

Hotkeys use `+` between modifiers and the key. Supported modifiers are
`Ctrl`, `Alt`, `Shift` and `Win`. The final key can be a letter (`A`–`Z`), a
digit (`0`–`9`), a function key (`F1`–`F24`), or one of `Backspace`, `Tab`,
`Enter`, `Escape`, `Space`, `PageUp`, `PageDown`, `End`, `Home`, an arrow key,
`Insert` or `Delete`. For example: `Ctrl+Shift+F12` or `Win+Alt+F`.

## Start hidden

The `--tray` argument starts fman with its window hidden in the tray. It is
also used by the optional Windows sign-in startup entry. If another fman
instance is already running, a launch with `--tray` is forwarded to that
instance without opening a second window.

These tray, hotkey and sign-in startup features are Windows-only. The
start-with-Windows command is available only in the installed build; development
and portable builds report that it is unavailable.
