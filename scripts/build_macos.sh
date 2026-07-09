#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$ROOT/src"
ASSETS="$ROOT/assets"
DEPS="$ROOT/vendor/deps"
cd "$ROOT"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "LJM-Java-Manager" \
  --icon "$ASSETS/build/java.icns" \
  --hidden-import plistlib \
  --hidden-import hashlib \
  --hidden-import locale \
  --hidden-import socket \
  --hidden-import stat \
  --add-data "$ASSETS/java.ico:." \
  --add-data "$DEPS:deps" \
  "$SRC/LJM.pyw"

chmod +x "$ROOT/dist/LJM-Java-Manager.app/Contents/MacOS/LJM-Java-Manager"

echo "macOS build finished: $ROOT/dist/LJM-Java-Manager.app"
