# Scripting API

The scripting API lets local scripts read fman's pane state and run commands.
It is disabled by default. Run **Toggle scripting API** from the command
palette to start or stop it; the status bar shows the URL and token file path
when it starts. The command takes effect immediately. If fman starts with the
API enabled in settings, it starts after plugins load.

## Connect

By default, the server listens only on this computer at
`http://127.0.0.1:47447`. Every request must include a bearer token. fman
creates the token in `%APPDATA%/fman/Local/ScriptingApiToken.txt` the first
time the API starts and reuses it on later starts. Keep this file secret: the
token grants access to every command allowed by the current settings.

Requests use UTF-8 JSON. Browser requests that include an `Origin` header are
rejected. Request bodies are limited to 1 MB. Every error response is a JSON
object with an `error` message.

## Endpoints

| Method and path | Request | Successful response |
| --- | --- | --- |
| `GET /v1/state` | — | `{"active_pane": 0, "panes": [{"path": "<url>", "cursor": null, "selection": ["<url>"]}]}` |
| `GET /v1/commands` | — | `{"pane": [<names>], "application": [<names>], "allowed": [<names>] or `null`}` |
| `POST /v1/command` | `{"name": "open_directory", "args": {"url": "file://C:/temp"}, "pane": 1}` | `{"ok": true}` |

The panes are listed active-first, so the active pane has index `0` and
`active_pane` is always `0`. A pane's `path`, `cursor` and `selection` values
are fman URLs; `cursor` is `null` when there is no file under the cursor.
For command requests, `args` defaults to `{}` and `pane` defaults to the
active pane. The `pane` field is ignored for application commands. Names are
looked up among pane commands first, then application commands.

The command response is sent when the command returns; a copy or move may
continue running in the background after that.

The server checks the requested command name against the allowlist before
dispatch. A plugin's `on_command` hook may rewrite a command after this
check, so the rewritten name is not checked a second time.

Error status codes:

| Status | Meaning |
| --- | --- |
| 400 | Invalid JSON, invalid fields, or a pane index outside the current panes |
| 401 | Missing or invalid bearer token |
| 403 | Browser Origin, disallowed client address, or command not allowed |
| 404 | Unknown endpoint or command |
| 413 | Request body is larger than 1 MB |

## Settings

Settings are in `%APPDATA%/fman/Local/Settings.json`:

```json
"scripting_api": {
  "enabled": false,
  "port": 47447,
  "allowed_hosts": [],
  "command_access": "allowlist",
  "allowed_commands": ["…defaults…"]
}
```

- `enabled` defaults to `false`. The command palette switch updates this value
  and applies it immediately. Changes to other settings apply the next time
  the API starts.
- `port` defaults to `47447` and must be between 1 and 65535.
- `allowed_hosts` defaults to an empty list. With no entries, the server binds
  to `127.0.0.1`. When entries are present, it binds to `0.0.0.0` and accepts
  loopback connections plus client addresses matching an entry. Entries can
  be IP addresses or CIDR networks; invalid entries are ignored with a log
  warning.
- `command_access` is `"allowlist"` by default. Set it to `"all"` to allow
  every command. An invalid value falls back to `"allowlist"`.
- `allowed_commands`, when provided, replaces the defaults. The default list
  is `move_cursor_up`, `move_cursor_down`, `move_cursor_home`,
  `move_cursor_end`, `move_cursor_page_up`, `move_cursor_page_down`, `go_up`,
  `go_back`, `go_forward`, `open_directory`, `reload`, `select_all`,
  `deselect`, `invert_selection`, `toggle_selection`, `switch_panes`,
  `toggle_hidden_files`, `sort_by_column`, `copy_paths_to_clipboard`,
  `copy_file_path`, `copy_file_name`, `center_window` and `minimize`.

The default list excludes destructive or externally launching commands, such
as deleting, renaming, moving, pasting, creating, opening files or launching a
terminal. It also excludes `toggle_scripting_api`; an API client cannot use
the default allowlist to change the API's own state.

## Security

HTTP traffic is unencrypted. Keep the default loopback-only binding unless LAN
access is needed. When `allowed_hosts` enables LAN access, anyone who can
connect from an allowed address and obtain the token can use all commands
permitted by `command_access` and `allowed_commands`. Do not share the token
file. Use a trusted network when enabling LAN access.

The allowlist limits command names, but fman plugins can rewrite commands
through `on_command` after the check. Use `command_access: "all"` only when
you trust every program that can reach the server and has the token.

## Examples

In the examples, replace `<token>` with the contents of
`ScriptingApiToken.txt`.

### curl

```sh
curl -H "Authorization: Bearer <token>" \
  http://127.0.0.1:47447/v1/state

curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"open_directory","args":{"url":"file://C:/Windows"}}' \
  http://127.0.0.1:47447/v1/command
```

### PowerShell

```powershell
$token = (Get-Content "$env:APPDATA\fman\Local\ScriptingApiToken.txt" -Raw).Trim()
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Headers $headers -Uri 'http://127.0.0.1:47447/v1/state'

$body = @{ name = 'open_directory'; args = @{ url = 'file://C:/Windows' } } |
    ConvertTo-Json -Compress
Invoke-RestMethod -Method Post -Headers $headers -ContentType 'application/json' `
    -Body $body -Uri 'http://127.0.0.1:47447/v1/command'
```

### Python

```python
import json
from pathlib import Path
import os
from urllib.request import Request, urlopen

token_path = Path(os.environ['APPDATA']) / 'fman' / 'Local' / 'ScriptingApiToken.txt'
token = token_path.read_text(encoding='utf-8').strip()
headers = {'Authorization': f'Bearer {token}'}

with urlopen(Request('http://127.0.0.1:47447/v1/state', headers=headers)) as response:
    state = json.load(response)
print(state)

body = json.dumps({
    'name': 'open_directory',
    'args': {'url': 'file://C:/Windows'},
}).encode('utf-8')
request = Request(
    'http://127.0.0.1:47447/v1/command',
    data=body,
    headers={**headers, 'Content-Type': 'application/json'},
    method='POST',
)
with urlopen(request) as response:
    print(json.load(response))
```
