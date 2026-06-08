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
  --onefile \
  --console \
  --name "LJM-Java-Manager-headless" \
  --add-data "$SRC/LJM_headless.pyw:." \
  --add-data "$SRC/LJM.pyw:." \
  --add-data "$ASSETS/java.ico:." \
  --add-data "$DEPS:deps" \
  "$SRC/LJM_headless_entry.py"

echo "Linux headless build finished: $ROOT/dist/LJM-Java-Manager-headless"
