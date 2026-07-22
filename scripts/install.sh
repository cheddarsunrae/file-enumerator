#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/usr/local}"

cd "$SCRIPT_DIR"

if [[ "$PREFIX" == /usr/local || "$PREFIX" == /usr ]]; then
    if [[ ${EUID} -eq 0 ]]; then
        make install PREFIX="$PREFIX"
    elif command -v sudo >/dev/null 2>&1; then
        sudo make install PREFIX="$PREFIX"
    else
        printf 'ERROR: root privileges are required to install under %s\n' "$PREFIX" >&2
        exit 1
    fi
else
    make install PREFIX="$PREFIX"
fi
