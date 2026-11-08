# Syncing settings between computers

When you sign in to the same fman account, fman can keep your keyboard
shortcuts and command palette names in sync across computers. Settings are
stored separately for Windows, Mac and Linux.

## What is synced

fman syncs the user copies of these four files:

- `Key Bindings (<OS>).json`
- `Viewer Key Bindings (<OS>).json`
- `Command Titles (<OS>).json`
- `Command Keywords (<OS>).json`

These files contain your own shortcuts, renamed commands and extra search
keywords. fman does not upload the built-in defaults. An absent user file is
treated as empty. The files remain local to each computer; fman stores a
separate sync record at `Local/Settings Sync.json` under the fman data folder.

## When settings sync

fman checks settings after startup, after you sign in, and whenever you run
*Sync settings* from the command palette. An edit made in fman's shortcut or
command palette editors is sent right away. If you edit a settings file by
hand, fman notices that change at the next startup or when you run *Sync
settings*.

## Choosing between different copies

If both this computer and your account have changed the same setting since the
last sync, fman asks which copy to keep. Choose *Keep this computer's*, *Use
the account's*, or *Combine both*. Combining keeps this computer's value when
both copies define the same shortcut or command, and adds entries found only
in the account copy. The choice applies to one settings file at a time.

Pressing Escape leaves both copies unchanged. fman asks again the next time it
syncs that setting.

On a computer's first sync, fman asks when the local file and the account copy
differ. If they match, or one side is empty, fman can sync without asking.

## Signed out or offline

When you are signed out, shortcuts and command palette edits continue to work
with the local files as usual. fman does not sync them until you sign in. If a
sync cannot reach the API, your local files remain available; run *Sync
settings* again after reconnecting.
