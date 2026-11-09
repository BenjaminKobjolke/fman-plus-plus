# Run as administrator

Run a local file with administrator rights. Windows displays its usual User
Account Control prompt before starting the file.

## Usage

1. Put the cursor on a program, batch file, installer or another local file.
2. Open the command palette and search for **Run as administrator**, or
   right-click the file and choose **Run as administrator**.
3. Approve the Windows prompt to start the file with administrator rights.

When several files are selected, fman starts each one separately, so Windows
may show a prompt for each file. Folders cannot be run this way.

## Commands

| Command name | Palette label | Keywords | Default key binding |
|--------------|---------------|----------|---------------------|
| `run_as_administrator` | Run as administrator | admin, elevated, elevate, uac, runas | none |

You can add a key binding in `Key Bindings.json`, for example:

```json
{ "keys": ["Ctrl+Shift+Enter"], "command": "run_as_administrator" }
```

## Notes

- This command is available on Windows only.
- Canceling the Windows prompt leaves fman open without showing an error.
- Windows decides whether a file type supports the `runas` action. If it
  cannot run the selected file, fman shows the error reported by Windows.
