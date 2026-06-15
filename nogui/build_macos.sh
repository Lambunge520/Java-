#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --console \
  --name "LJM-Java-Manager-nogui" \
  --add-data "$ROOT/LJM_nogui.pyw:." \
  --add-data "$ROOT/LJM.pyw:." \
  --add-data "$ROOT/java.ico:." \
  --add-data "$ROOT/deps:deps" \
  "$ROOT/LJM_nogui_entry.py"

cat > "$ROOT/dist/LJM-Java-Manager-nogui.command" <<'EOF'
#!/usr/bin/env sh
set -eu
APP_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd)"
exec "$APP_DIR/LJM-Java-Manager-nogui" "$@"
EOF

chmod +x "$ROOT/dist/LJM-Java-Manager-nogui" "$ROOT/dist/LJM-Java-Manager-nogui.command"

echo "macOS nogui build finished: $ROOT/dist/LJM-Java-Manager-nogui.command"
