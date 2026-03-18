#!/usr/bin/env bash
# setup.sh — install deps and register the `buddy` command
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "→ Installing Python dependencies..."
if pip install numpy imageio imageio-ffmpeg 2>/dev/null; then
    echo "  done."
elif pip install numpy imageio imageio-ffmpeg --break-system-packages 2>/dev/null; then
    echo "  done (--break-system-packages)."
else
    echo ""
    echo "pip install failed. If you're using conda/venv, activate it first:"
    echo "  conda activate <env>  or  source venv/bin/activate"
    echo "Then re-run: bash setup.sh"
    exit 1
fi

echo "→ Making buddy.sh executable..."
chmod +x "$SCRIPT_DIR/buddy.sh"

INSTALL_PATH="/usr/local/bin/buddy"

if command -v sudo &>/dev/null; then
    echo "→ Linking $SCRIPT_DIR/buddy.sh → $INSTALL_PATH"
    sudo ln -sf "$SCRIPT_DIR/buddy.sh" "$INSTALL_PATH"
    echo "✓ Done. Run: buddy video.mp4"
else
    echo ""
    echo "No sudo available. Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$PATH:$SCRIPT_DIR\""
    echo "Then: source ~/.bashrc && buddy video.mp4"
fi