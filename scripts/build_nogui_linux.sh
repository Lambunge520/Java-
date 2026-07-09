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
  --name "LJM-Java-Manager-nogui" \
  --hidden-import plistlib \
  --hidden-import hashlib \
  --hidden-import locale \
  --hidden-import socket \
  --hidden-import stat \
  --add-data "$SRC/LJM_nogui.pyw:." \
  --add-data "$SRC/LJM.pyw:." \
  --add-data "$ASSETS/java.ico:." \
  --add-data "$DEPS:deps" \
  "$SRC/LJM_nogui_entry.py"

cat > "$ROOT/dist/LJM-Java-Manager-nogui.run" <<'EOF'
#!/usr/bin/env sh
set -eu
APP_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd)"
exec "$APP_DIR/LJM-Java-Manager-nogui" "$@"
EOF

chmod +x "$ROOT/dist/LJM-Java-Manager-nogui" "$ROOT/dist/LJM-Java-Manager-nogui.run"

echo "Linux nogui build finished: $ROOT/dist/LJM-Java-Manager-nogui.run"
