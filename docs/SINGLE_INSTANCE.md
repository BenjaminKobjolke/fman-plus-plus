# Single instance

By default fman runs as a **single instance**. Launching `fman` again while it is
already running does not open a second window — the running instance handles the
launch instead.

## Behavior

- `fman "C:\some\folder"` → the running fman comes to the front and opens the
  folder in the **active pane**.
- `fman "C:\some\file.txt"` → the running fman opens the file's parent folder in
  the active pane and places the cursor on the file.
- `fman` (no path) → the running fman window is simply raised/focused.
- `fman --single-pane` → the running fman hides the other panes, then comes to
  the front. On a fresh start, the same option starts with one visible pane.
- Multiple paths (`fman "C:\a" "C:\b"`) → the first path opens in the active pane,
  the next in the other pane, and so on, matching the fresh-start behavior.

If no instance is running, fman starts normally.

## Disabling it

To allow multiple independent fman windows again, set `single_instance` to
`false` in the app settings file:

    <DataDirectory>/Local/Settings.json

```json
{
  "single_instance": false
}
```

The default is `true` (single instance on). Create the file if it does not exist.

## How it works

The first instance listens on a per-user local socket
(`QLocalServer`/`QLocalSocket`). A later launch connects to that socket, sends its
(absolute) path arguments as a JSON object with `paths` and `single_pane`, and
exits. The primary instance also accepts the older plain JSON path-list payload,
which implies `single_pane: false`. It receives the message on its Qt event loop,
raises its window, and opens the paths via the same path-resolution logic used at
startup (`SessionManager.open_path_in_pane`).

The socket name is derived from the fman data directory
(`fman-si-<hash>`), so different OS users and installs never collide. If the
socket cannot be created, fman logs a warning and just starts a normal instance —
IPC problems never block startup.
