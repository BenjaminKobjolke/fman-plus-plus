# Check for updates

fman checks the latest published GitHub release five minutes after its main
window appears, then every 24 hours while it remains open. The automatic check
does not run in demo mode. It stays quiet when the app is current or the check
fails. When a newer release exists, a dialog names both versions and offers to
download and install it. The download shows a cancelable progress dialog.

On Windows, fman runs the downloaded installer and quits so the update can be
installed. On macOS, fman opens the downloaded `fman.dmg` and stays open. Linux
has no installer asset, so fman opens the GitHub releases page. If a download
fails, fman shows an alert and opens that page as a fallback. Each release is
announced automatically only once.

You can check at any time from the command palette (`Ctrl+Shift+P`). The manual
command always reports the result, including an up-to-date or failed check, and
offers to download the update even if it has announced that release before.

## Commands

| Command name | Palette label | Keywords | Default key binding |
| --- | --- | --- | --- |
| `check_for_updates` | Check for updates | update, upgrade, new version, latest release, github | none |

The installed release label comes from the newest bundled `release_notes/`
folder. When there are no bundled notes, it uses the application version with
build `0`. GitHub's latest published release tag must use the same
`<version>_<build>` form.

An internal build with no new release notes may read as the previous public
release. A source checkout reads as the newest authored release notes. Neither
case identifies a distinct internal build. A stalled GitHub connection can keep
one daemon worker occupied; the UI remains responsive.
