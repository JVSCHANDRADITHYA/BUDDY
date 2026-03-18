#!/usr/bin/env bash
# build_release.sh — produces a single self-contained binary via PyInstaller
#
# Usage:
#   pip install pyinstaller
#   bash build_release.sh
#
# Output: dist/ascii_play  (Linux/macOS)  or  dist/ascii_play.exe  (Windows)
# The binary includes Python, numpy, imageio, and the bundled FFmpeg binary.
# End users need nothing installed — just run the binary.

set -e

echo "→ Installing build deps..."
pip install pyinstaller --quiet

# Find the imageio_ffmpeg bundled ffmpeg binary so PyInstaller can include it
FFMPEG_DIR=$(python -c "import imageio_ffmpeg, os; print(os.path.dirname(imageio_ffmpeg.__file__))")
echo "→ FFmpeg data dir: $FFMPEG_DIR"

pyinstaller \
  --onefile \
  --name ascii_play \
  --add-data "$FFMPEG_DIR:imageio_ffmpeg" \
  --hidden-import imageio_ffmpeg \
  --hidden-import numpy \
  --strip \
  ascii_play/cli.py

echo ""
echo "✓ Build complete: dist/ascii_play"
echo "  Size: $(du -sh dist/ascii_play | cut -f1)"
