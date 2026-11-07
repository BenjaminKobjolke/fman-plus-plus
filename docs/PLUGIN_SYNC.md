# Syncing plugins between computers

Sign in to a fman account to keep one list of third-party plugins across your
computers. fman syncs plugin names, sources and versions only; it does not
sync plugin settings or other files.

## Sign in and sign out

Run *Sign in to fman account* from the command palette. fman opens the account
sign-in page in your browser and polls the fman API until sign-in finishes.
The deployed sign-in service does not accept a loopback redirect address, so
fman starts sign-in without one and waits for the API callback instead. The
access token is saved in the operating system credential store under service
`fman++ API` and user `access_token`; it is not written to a settings JSON
file. fman refreshes the token when it uses the account API. Run *Sign out of
fman account* to remove the token from this computer. Signing out does not
delete the shared list.

## Install and remove hooks

When signed in, a successful *Install plugin* adds or replaces that plugin's
entry in the shared list. *Remove plugin* deletes its entry. GitHub, GitLab and
Forgejo entries store the repository URL and the installed release tag or
commit SHA. Catalog entries store the catalog plugin name and release version.
Both include the operating system and fman version that saved the entry. A plugin without
source metadata, such as one copied into the third-party folder by hand, is
not uploaded.

## Automatic and manual sync

fman runs *Sync plugins* once after startup when the first pane becomes ready.
You can also run *Sync plugins* from the command palette. It compares the
account list, installed third-party plugins and the last sync state saved on
this computer:

- A plugin in the account list but not installed here is offered in one
  checklist. Entries saved on this operating system start checked; entries
  saved on another operating system start unchecked and show that system.
  Selected entries are installed at the saved version, not the latest one.
- A plugin previously shared from this computer but removed from the account
  list is presented for removal here. fman deletes the local copy only after
  you confirm. If you decline, it stays pending and fman asks again at a
  later sync.
- A plugin installed here with recognized source metadata but missing from
  the account list is uploaded. Plugins without source metadata are skipped.
- A plugin removed here while the computer was offline is deleted from the
  account list at the next successful sync.

If an install from the checklist is skipped or left unchecked, fman remembers
that choice for that plugin version. It is offered again when its saved
version changes. An inclusive sync (`include_ignored=true`) can offer the same
version again. A network or API failure reports a status message; the next
sync compares the current local and remote state again.

The per-computer state is saved in `Local/Plugin Sync.json` under fman's data
directory. It contains the names already synchronized from this computer and
the remote versions the user chose to ignore. Keep this file local to the
computer; it is not part of the shared plugin list.

## API contract

The client uses the production API at `https://fman.workflow-tools.com/`.
Account list operations require a Bearer access token:

- `GET /api/v1/plugin-list?limit=200` returns the caller's list in
  `{"plugins": [...], "total": 1, "limit": 200, "offset": 0}` form. Each
  plugin has `name`, `source`, `location`, `version`, `os`, `fman_version` and
  server-managed `updated_at` fields.
- `PUT /api/v1/plugin-list/{name}` adds or replaces an entry. Its JSON body
  contains `name`, `source`, `location`, `version`, `os` and `fman_version`.
- `DELETE /api/v1/plugin-list/{name}` removes the named entry.

`source` is `github`, `catalog`, `gitlab` or `forgejo`. `os` is `Windows`,
`Mac` or `Linux`.
GitHub `location` is a repository URL such as
`https://github.com/owner/repository`; catalog `location` is the catalog
plugin name. GitLab and Forgejo `location` values are HTTPS repository web
URLs, including for self-hosted servers. When reading the account list, this
client skips entries with an unknown or invalid source so one newer entry does
not prevent older entries from syncing. The API isolates each list to the
signed-in account.
