# Explorer replacement

On Windows, the command palette command **Toggle Explorer replacement** lets an
installed copy of fman handle common folder-opening actions. The setting is
`explorer_replacement` in `Local/Settings.json`; it is off by default.

When enabled, opening a folder or drive, pressing **Win+E**, or opening **This
PC** brings up fman. A folder or drive opens in the active pane when fman is
already running. This PC opens fman's drives view. Control Panel, the Recycle
Bin and other special folders continue to open in Explorer. The right-click
**Open** action also remains Explorer's action. Portable and development builds
cannot enable this mode because Windows stores the executable's current path.

If another program changes the folder-opening handler, fman detects the change
the next time it starts. It removes its remaining redirect entries, turns the
setting off, and reports that another program now opens folders. You can then
enable the mode again from the command palette if you want fman to take over.

F10 (**Open native file manager**) opens the real Explorer window even while
replacement is enabled. Uninstalling fman removes its folder, drive, Win+E and
This PC registry entries before deleting the program files.

## Undo by hand

To turn off the redirect manually, remove the `fman` subkeys under
`HKEY_CURRENT_USER\Software\Classes\Directory\shell` and
`HKEY_CURRENT_USER\Software\Classes\Drive\shell`. If either `shell` key has
its default value set to `fman`, delete that default value too.

Also remove these keys if their command still points to fman's executable:

- `HKEY_CURRENT_USER\Software\Classes\CLSID\{52205fd8-5dfb-447d-801a-d0b52f2e83e1}`
- `HKEY_CURRENT_USER\Software\Classes\CLSID\{20D04FE0-3AEA-1069-A2D8-08002B30309D}`

Windows refreshes file associations when fman changes the setting. After a
manual edit, sign out and back in if Explorer does not immediately use the
restored handlers.

An all-users installation removed by a different administrator account using
over-the-shoulder UAC can only clean that administrator's per-user registry.
Turn the mode off before uninstalling in that situation, or remove the keys
above from the user account that enabled it.
