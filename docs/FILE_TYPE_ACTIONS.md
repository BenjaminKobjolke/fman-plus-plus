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

On macOS, app choices from the Open with list use the system's `open -a` handling. A custom
command line runs the selected executable path directly, so selecting a `.app` bundle may require
its inner executable instead.
