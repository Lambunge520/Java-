#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "LJM-Java-Manager" \
  --icon "$ROOT/build_assets/java.icns" \
  --add-data "$ROOT/java.ico:." \
  --add-data "$ROOT/deps:deps" \
  "$ROOT/LJM.pyw"

echo "macOS build finished: $ROOT/dist/LJM-Java-Manager.app"
