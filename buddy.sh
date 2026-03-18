#!/usr/bin/env bash
# buddy — terminal video player
# Usage: buddy video.mp4 [options]
#
# Setup (run once):
#   chmod +x buddy.sh
#   sudo ln -sf "$(pwd)/buddy.sh" /usr/local/bin/buddy
#   # or add this folder to PATH in ~/.bashrc:
#   # export PATH="$PATH:/path/to/ascii_play"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/ascii_play/cli.py" "$@"
