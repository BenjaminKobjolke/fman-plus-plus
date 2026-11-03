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

## Automatic updates

Automatic updates are off by default. In an installed Windows copy, use
**Toggle automatic updates** in the command palette to turn them on or off.
Use **Set automatic update interval** to choose how often fman checks, from 1
to 720 hours; the default is 24 hours. Automatic checks start five minutes after
the main window appears, then check at the selected interval.

When an update is available, fman shows a 30-second countdown with a progress
bar and **Update now** and **Cancel** buttons. Choose **Update now**, or let the
countdown finish, to download the update, close fman, install it without the
setup wizard, and restart fman. **Cancel** is the default button and Esc has the
same effect; either postpones the prompt until the next automatic check. The
download itself has a cancelable progress dialog. When automatic updates are
on, accepting a manual update also uses the wizard-free install; otherwise a
manual Windows update opens the setup wizard.

These commands are also listed in portable copies, but automatic updates only
work in an installed Windows version. Other versions, including portable
copies, show a message explaining this. Manually checking in a portable copy
downloads `fmanPortable.zip`; after you confirm, fman closes and replaces the
portable program files while keeping its data, then starts the updated copy.

An all-users installation in Program Files needs one UAC confirmation for each
automatic update. It remains in Program Files after the update.

## Commands

| Command name | Palette label | Keywords | Default key binding |
| --- | --- | --- | --- |
| `check_for_updates` | Check for updates | update, upgrade, new version, latest release, github | none |
| `toggle_automatic_updates` | Toggle automatic updates | auto update, automatic update, unattended update | none |
| `set_automatic_update_interval` | Set automatic update interval | update interval, update frequency, check frequency | none |

The installed release label comes from the newest bundled `release_notes/`
folder. When there are no bundled notes, it uses the application version with
build `0`. GitHub's latest published release tag must use the same
`<version>_<build>` form.

An internal build with no new release notes may read as the previous public
release. A source checkout reads as the newest authored release notes. Neither
case identifies a distinct internal build. A stalled GitHub connection can keep
one daemon worker occupied; the UI remains responsive.
