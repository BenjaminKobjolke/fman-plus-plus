#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

PYTHON=${FMAN_PYTHON:-.venv/bin/python}
LABEL=$("$PYTHON" tools/release/build_number.py label)
if ! TAG_COMMIT=$(git rev-parse "$LABEL^{commit}" 2>/dev/null) || \
	[[ "$TAG_COMMIT" != "$(git rev-parse HEAD)" ]]; then
	echo "ERROR: finish and push the Windows release, then run: git fetch --tags && git checkout $LABEL" >&2
	exit 1
fi

rm -f target/release_version.txt
"$PYTHON" build.py release_build
if [[ ! -f target/fman.dmg ]]; then
	echo "ERROR: build reported success but target/fman.dmg is missing." >&2
	exit 1
fi
printf '%s\n' "$LABEL" > target/release_version.txt
