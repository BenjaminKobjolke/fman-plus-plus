#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

PYTHON=${FMAN_PYTHON:-.venv/bin/python}
export FMAN_PYTHON="$PYTHON"
if [[ ! -x "$PYTHON" ]]; then
	echo "ERROR: Python interpreter not found or not executable: $PYTHON" >&2
	exit 1
fi

exec "$PYTHON" tools/fman_ui/fman_ui.py "$@"
