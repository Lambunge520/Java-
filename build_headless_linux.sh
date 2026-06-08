#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --console \
  --name "LJM-Java-Manager-headless" \
  --add-data "$ROOT/LJM_headless.pyw:." \
  --add-data "$ROOT/LJM.pyw:." \
  --add-data "$ROOT/java.ico:." \
  --add-data "$ROOT/deps:deps" \
  "$ROOT/LJM_headless_entry.py"

echo "Linux headless build finished: $ROOT/dist/LJM-Java-Manager-headless"
