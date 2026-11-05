#!/usr/bin/env bash
# ==============================================================================
# Dead as Disco - BPM & BeatSync Studio Unix Root Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIX_LAUNCHER="$SCRIPT_DIR/launchers/run_unix.sh"

if [ ! -f "$UNIX_LAUNCHER" ]; then
    echo "[ERROR] No se encontró el script / Script not found: $UNIX_LAUNCHER" >&2
    exit 1
fi

exec bash "$UNIX_LAUNCHER" "$@"
