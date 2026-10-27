# Build and publish the macOS release

The Mac release is an arm64 build made on Apple Silicon. It uses the same plain version label and GitHub Release as the Windows build; it does not bump the version.

## One-time setup

1. Install Xcode Command Line Tools.
2. Install [uv](https://docs.astral.sh/uv/) and create the build venv from the fman checkout:

   ```sh
   uv run --no-project python tools/fbs_pro.py
   uv sync
   ```

   `tools/build_mac.sh` uses `.venv/bin/python` unless `FMAN_PYTHON` is set.

3. Install and authenticate the GitHub CLI with `gh auth login`.
4. Check out [release-tool](https://github.com/BenjaminKobjolke/release-tool) and run `uv sync`. By default the scripts expect it at `$HOME/GIT/BenjaminKobjolke/release-tool`; set `RELEASE_TOOL_DIR` if it is elsewhere.
5. Follow release-tool's [Mac signing setup](https://github.com/BenjaminKobjolke/release-tool/blob/main/docs/MAC_PACKAGE_COMMAND.md): install the Developer ID Application certificate, store the notarization credentials with `xcrun notarytool store-credentials cmdai`, and configure `mac_signing.ini` with `app_identity` and `keychain_profile`. fman does not need a Developer ID Installer certificate. The signing command is release-tool's `mac-sign` (#11517); fman passes its app entitlements to that command.

Install mpv with `brew install mpv` to enable video previews.

## Build and publish

1. Complete and push the Windows release first. Its tag is the plain version, such as `1.8.0`. The release tooling bumps the patch automatically and rolls over after 10: `1.8.10` is followed by `1.9.0`.
2. In the fman checkout on the Mac, fetch and check out that tag:

   ```sh
   git fetch --tags && git checkout <version>
   ```

3. Build the app and disk image:

   ```sh
   ./tools/build_mac.sh
   ```

   This freezes fman, signs and notarizes the app, builds `target/fman.dmg`, signs and notarizes the disk image, and records the label in `target/release_version.txt`. Each signing and notarization operation runs through release-tool.

4. Optional local checks:

   ```sh
   spctl -a -vv target/fman.app
   xcrun stapler validate target/fman.dmg
   ```

5. Attach the disk image to the existing GitHub Release:

   ```sh
   ./tools/github_release_mac.sh
   ```

   The script uses the recorded version. Pass a version explicitly only when publishing a build that predates the record, for example `./tools/github_release_mac.sh 1.8.0`.
6. Return the checkout to the main branch with `git checkout main`.

The upload adds `fman.dmg` to the same release as `fmanSetup.exe` and keeps its title and notes unchanged.
