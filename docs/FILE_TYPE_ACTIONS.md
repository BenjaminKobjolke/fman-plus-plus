# File type actions

Choose what Enter and double-click do for a file type from **Open with... → Configure...**.
Select **Always open .md files with...** and choose an app, **fman viewer**, **fman editor
(F4)**, or **Command line...**. To restore the operating system association, select
**Stop always opening .md files with ...** for that suffix.

Actions are stored in the user data file `File Type Actions.json`. You can edit it directly:

```json
{
  ".md": {"command_line": ["C:\\Program Files\\Typora\\Typora.exe", "{file}"], "app": "Typora"},
  ".log": {"command": "view_file"},
  ".csv": {"command_line": ["C:\\Tools\\csvview.exe", "--sep", ";", "{file}"]}
}
```

`{file}` is replaced with the file's path in every argument. If it is omitted, it is added at
the end. The longest matching suffix wins, so `.tar.gz` can have its own action while `.gz`
remains the fallback for other gzip files. Suffix matching ignores case. Files without an
extension have no file type action.

When no action is configured, fman opens the file with the system default app. If an action is
invalid, its program is missing, or its fman command cannot run, fman shows a status message and
uses the system default for that file. Use the command palette entry **Open with system default**
to bypass a configured action for one opening.

Editing an app in **Open with → Configure → Edit app** updates file type actions that refer to
that app, including its new name and path. Removing an app from the Open with list leaves its file
type actions intact; the saved program path remains in use.

## Apps with arguments

Add app and Edit app ask for arguments after the program name. Press Enter with only `{file}` to
keep a plain app entry. `Apps.json` stores a command line as a string, for example
`"VLC": "flatpak run org.videolan.VLC {file}"` or
`"VLC": "\"C:\\Program Files\\VideoLAN\\VLC\\vlc.exe\" --fullscreen {file}"`.
A value that names an existing file is treated as a plain program path, preserving older entries.
When hand-editing a command line, quote a program path containing spaces so it can be separated
from its arguments.

With multiple selected files, a standalone `{file}` expands to all files in one launch. If it is
embedded in an argument such as `--file={file}`, the app launches once for each file.

On macOS, app choices from the Open with list use the system's `open -a` handling. A custom
command line, including an Open with app that has arguments, runs the selected executable path
directly, so selecting a `.app` bundle may require its inner executable instead.
