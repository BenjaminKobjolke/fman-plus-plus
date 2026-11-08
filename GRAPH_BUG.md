# graphify hook error: `graphify.EXE: No such file or directory`

## Symptom

While Claude Code runs in this repository, tool calls print:

```
C:/Users/XIDA/AppData/Roaming/Python/Python314/Scripts/graphify.EXE: No such file or directory
```

## Cause

`.claude/settings.local.json` registers two PreToolUse hooks with an absolute path to the
graphify executable (lines 32 and 41):

```json
"PreToolUse": [
  { "matcher": "Bash|Grep",
    "hooks": [{ "type": "command",
      "command": "C:/Users/XIDA/AppData/Roaming/Python/Python314/Scripts/graphify.EXE hook-guard search" }] },
  { "matcher": "Read|Glob",
    "hooks": [{ "type": "command",
      "command": "C:/Users/XIDA/AppData/Roaming/Python/Python314/Scripts/graphify.EXE hook-guard read" }] }
]
```

The path was written when graphify was installed with pip into the user site-packages of
Python 3.14. graphify is now installed as a uv tool:

- `Get-Command graphify -All` resolves only `C:\Users\XIDA\.local\bin\graphify.exe`
- `graphify --version` prints `graphify 0.9.93`
- `Test-Path "$env:APPDATA\Python\Python314\Scripts\graphify.exe"` is `False`

So every Bash, Grep, Read and Glob call starts a hook whose executable no longer exists.

Old transcripts (`~/.claude/jobs/4bdd2264/parent-transcript.jsonl`, 2026-10-30) show the same
hook command running successfully, so the old exe was removed after that date.

## Places checked that are not the cause

- `~/.claude/settings.json`: mentions graphify only in a permission note, no hook.
- `~/.claude/settings.local.json`, `.claude/settings.json`: no graphify entries.
- `.git/hooks`: no graphify entries.
- Shell profile: the old Scripts folder is still on `PATH` (seen in the shell snapshot), but
  that only adds a dead directory, it does not cause the error.

## Fix

Replace both commands in `.claude/settings.local.json` with the PATH-resolved name, so a future
reinstall cannot break them again:

```json
"command": "graphify hook-guard search"
"command": "graphify hook-guard read"
```

Alternative: re-run `graphify claude install` in this repository so graphify rewrites the hooks
with its current location. That writes an absolute path again.

Restart Claude Code afterwards; hooks are read at session start.

## Verify

- `graphify hook-guard search` runs in a shell without error.
- In a new Claude Code session, a Grep call shows the graphify reminder and no
  "No such file or directory" error.

## Open points

- Other repositories where `graphify claude install` ran before the move probably have the same
  stale path in their `.claude/settings.local.json`. Search for `Python314/Scripts/graphify`.
- Optional cleanup: remove `C:\Users\XIDA\AppData\Roaming\Python\Python314\Scripts` from `PATH`
  if nothing else lives there.
