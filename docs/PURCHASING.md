# Purchasing

There is nothing to buy. **Every installation of this fork is activated.**

No license, no license key, no trial period, no registration, no feature gating,
no "unregistered" nag screen. fman starts straight into the file manager, every
time.

## What was removed

Upstream fman is commercial software with a paid license. This fork deleted that
machinery outright rather than leaving it dormant:

- **The key validator** — `src/main/python/fman/impl/licensing.py`. An offline
  RSA check: `<DataDirectory>/Local/User.json` held an `email` plus a
  base64/RSA-signed `key` that had to decrypt to matching JSON. It also carried a
  hardcoded blocklist of revoked keys and an optional `max_version` that expired
  a license against newer fman builds.
- **The nag dialog** — `SplashScreen` in `src/main/python/fman/impl/widgets.py`.
  Shown on every start of an unlicensed copy. It offered three buttons (A/B/C),
  only one of which — picked at random — dismissed it; the other two quit fman.
  Escape was blocked, and roughly every tenth run the "obtain a license" link was
  rendered bright green to be harder to ignore.
- **The window-title marker** — the title read `fman – NOT REGISTERED` when
  unlicensed. It now always reads `fman` before the Core plugin takes over (see
  [WINDOW_TITLE_AND_BARS.md](WINDOW_TITLE_AND_BARS.md)).
- **The `install_license_key` command** and the listener that offered to install
  any file named `User.json` you tried to open, both in
  `src/main/resources/base/Plugins/Core/core/commands/` (the command
  package - both were deleted before it was split into modules).
- **The registration line in `About`** — the About dialog now shows only the fman
  version.
- **The `BUY` and `LOGIN` links** — removed from `src/main/python/fman/links.py`
  and from [EXTERNAL_LINKS.md](EXTERNAL_LINKS.md).
- **The licensing telemetry** — `application_context.py` used to send the
  licensee's email address to `fman.io` the first time a key was installed. That
  call is gone with the code around it.

The `rsa` dependency went with the validator and is no longer in
`pyproject.toml`.

## Leftover files in your data directory

Neither of these is read any more; both are harmless:

- `<DataDirectory>/Local/User.json` — an old license key. Ignored. You can delete
  it.
- `<DataDirectory>/Local/Session.json` — may still contain a stale `is_licensed`
  entry from an older build. Ignored, and no longer written.

## No license server

There never was one. Validation was entirely offline — the RSA public key was
baked into the binary — so removing the check contacts nothing and breaks
nothing. The only licensing-adjacent network traffic was the telemetry ping
mentioned above.

## For maintainers

Do not re-add any of this. If you are rebranding the fork, the place to change
user-facing URLs is `src/main/python/fman/links.py`, documented in
[EXTERNAL_LINKS.md](EXTERNAL_LINKS.md) — it deliberately no longer has a purchase
link.
