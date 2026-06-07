#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "LJM-Java-Manager" \
  --add-data "$ROOT/java.ico:." \
  --add-data "$ROOT/build_assets/java.png:." \
  --add-data "$ROOT/deps:deps" \
  "$ROOT/LJM.pyw"

mkdir -p "$ROOT/dist/linux-desktop"
cp "$ROOT/build_assets/ljm-java-manager.desktop" "$ROOT/dist/linux-desktop/"
cp "$ROOT/build_assets/java.png" "$ROOT/dist/linux-desktop/"

echo "Linux build finished: $ROOT/dist/LJM-Java-Manager"
