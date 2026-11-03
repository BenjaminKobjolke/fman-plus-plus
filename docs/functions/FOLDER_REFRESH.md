# Folder refresh

fman can periodically re-read open folders so changes made by other programs
appear without leaving the folder. Windows filesystem watchers are disabled
because they can keep drives locked, so this feature polls without holding a
watcher handle between refreshes. It only runs while fman is the active window;
switching back to fman already refreshes both panes.

Use the command palette to toggle refresh independently for local folders,
network folders and FTP folders:

- `Toggle local folder refresh`
- `Toggle network folder refresh`
- `Toggle FTP folder refresh`

Each category is off by default and has its own interval, defaulting to five
seconds. The toggles take effect immediately. Edit `Core Settings.json` to
change these six settings:

| Setting | Default | Purpose |
| --- | --- | --- |
| `refresh_local_folders` | `false` | Enable refresh for local folders |
| `local_folder_refresh_seconds` | `5` | Local folder interval in seconds |
| `refresh_network_folders` | `false` | Enable refresh for network folders |
| `network_folder_refresh_seconds` | `5` | Network folder interval in seconds |
| `refresh_ftp_folders` | `false` | Enable refresh for FTP, FTPS and SFTP folders |
| `ftp_folder_refresh_seconds` | `5` | FTP folder interval in seconds |

Hand-edited interval changes take effect the next time you change folders.
FTP providers show their usual “Loading…” and “Ready.” status messages on each
refresh.
