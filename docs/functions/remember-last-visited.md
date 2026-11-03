# Remember last visited item

When you return to a location, fman selects the file or subfolder you last had
under the cursor there. It remembers each level of a visited path, so after
visiting a deep folder, its parent selects the next folder in that path. The
selection is saved across restarts and works with local folders, archives,
FTP/SFTP locations and plugin locations.

The feature is enabled by default. Set `remember_last_visited` in
`Core Settings.json` to `false` to disable it, or use **Toggle remember last
visited** in the command palette to switch it while fman is open. Existing
history remains when the setting is off; no new entries are recorded and none
are selected.

**Clear last visited history** empties the saved history. Incognito mode does not
record new visits, but it can still select an item remembered earlier.

History is stored in `Last Visited.json`, next to `Visited Paths.json`, with a
maximum of 1,000 locations. When the cap is exceeded, the oldest entries are
dropped first. Entries remain until displaced by newer visits or cleared by the
user.

For remote URLs with a password in the authority, fman removes the password
before saving or looking up the location. User and host names are retained, as
the feature applies to every location type.
