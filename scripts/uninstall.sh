#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-/usr/local}"

cd "$SCRIPT_DIR"

if [[ "$PREFIX" == /usr/local || "$PREFIX" == /usr ]]; then
    if [[ ${EUID} -eq 0 ]]; then
        make uninstall PREFIX="$PREFIX"
    elif command -v sudo >/dev/null 2>&1; then
        sudo make uninstall PREFIX="$PREFIX"
    else
        printf 'ERROR: root privileges are required to uninstall from %s\n' "$PREFIX" >&2
        exit 1
    fi
else
    make uninstall PREFIX="$PREFIX"
fi
