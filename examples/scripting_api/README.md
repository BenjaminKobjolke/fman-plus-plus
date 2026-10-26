# Scripting API examples

Small clients for fman's [scripting API](../../docs/SCRIPTING_API.md). Turn the
API on first with **Toggle scripting API** in the command palette. Every
script reads the token from `%APPDATA%\fman\Local\ScriptingApiToken.txt` and
uses `http://127.0.0.1:47447` unless the `FMAN_API_URL` environment variable
says otherwise.

| File | Needs | Try |
| --- | --- | --- |
| `fman_api.py` | Python 3 | `python fman_api.py state` |
| `fman_api.ps1` | PowerShell 5.1 or 7 | `.\fman_api.ps1 command open_directory -Arguments @{ url = 'file://C:/Windows' }` |
| `fman_api.bat` | `curl.exe` (Windows 10+) | `fman_api.bat open C:\Windows` |
| `fman_api.ahk` | AutoHotkey v2 | run it, then press Ctrl+Alt+S |

The Python, PowerShell and batch scripts all take `state`, `commands` and
`command <name>`. The AutoHotkey script binds hotkeys instead; see the comment
at its top. Ctrl+Alt+E opens the folder of the active Explorer window in fman.

Commands outside the allowlist answer `403 Command is not allowed.`. See
[Settings](../../docs/SCRIPTING_API.md#settings) to change the allowlist.
