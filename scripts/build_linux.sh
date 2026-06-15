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
  --windowed \
  --name "LJM-Java-Manager" \
  --add-data "$ASSETS/java.ico:." \
  --add-data "$ASSETS/build/java.png:." \
  --add-data "$DEPS:deps" \
  "$SRC/LJM.pyw"

cat > "$ROOT/dist/LJM-Java-Manager.run" <<'EOF'
#!/usr/bin/env sh
set -eu
APP_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd)"
exec "$APP_DIR/LJM-Java-Manager" "$@"
EOF

chmod +x "$ROOT/dist/LJM-Java-Manager" "$ROOT/dist/LJM-Java-Manager.run"

mkdir -p "$ROOT/dist/linux-desktop"
cp "$ASSETS/build/ljm-java-manager.desktop" "$ROOT/dist/linux-desktop/"
cp "$ASSETS/build/java.png" "$ROOT/dist/linux-desktop/"

echo "Linux build finished: $ROOT/dist/LJM-Java-Manager.run"
