#!/usr/bin/env bash
# buddy — terminal video player
# This script resolves its own real location even when called via symlink.

# Follow symlinks to find the actual script location
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

exec python3 "$SCRIPT_DIR/ascii_play/cli.py" "$@"