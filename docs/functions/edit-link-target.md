# Edit link target

Change the destination of a symbolic link, directory junction or Windows
`.lnk` shortcut without deleting and recreating it yourself.

## Usage

Put the cursor on a supported link and choose **Edit link target** from the
command palette (`Ctrl+Shift+P`) or the Windows file context menu. The current
destination is selected in the input box. Enter a new path and press Enter;
cancel, leave it blank or keep the current destination to make no change.

| Command name       | Palette label      | Keywords                                                       | Default key binding |
|--------------------|--------------------|----------------------------------------------------------------|---------------------|
| `edit_link_target` | Edit link target   | symlink, junction, shortcut, lnk, link target, retarget, change link, mklink | none                |

## Supported links

- Symbolic links can point to files or folders. Relative targets stay relative
  to the link's folder.
- Directory junctions and `.lnk` shortcuts use an absolute target path.
- `.lnk` shortcut arguments, icon and working directory are preserved.
- The command is available only for local links. Windows shortcuts are Windows
  only; symbolic links are subject to the operating system's permissions.
- Creating symbolic links on Windows may require Developer Mode or an
  administrator account. If Windows refuses the change, fman reports the error
  and keeps the existing link.

## Missing destinations

When the new target does not exist, fman asks whether to point the link there
anyway. Choose **Yes** to continue or **No** to keep the current destination.

## Implementation

- `core/commands/link_target.py` implements the command and safely replaces
  symbolic links and junctions through a temporary link in the same folder.
- `core/commands/util.py` reads and updates Windows shortcut targets through
  `WScript.Shell`.
- `core/tests/commands/test_link_target.py` covers visibility, retargeting,
  missing targets and failure behavior.
