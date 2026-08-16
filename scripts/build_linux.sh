#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$ROOT/src"
ASSETS="$ROOT/assets"
DEPS="$ROOT/vendor/deps"
cd "$ROOT"

# vendor/deps carries wheels for every platform; only the directory matching
# this build machine may go into the binary, otherwise one package would ship
# components for all three operating systems.
case "$(uname -m)" in
  x86_64|amd64) PLATFORM_DEPS_NAME="linux-x86_64" ;;
  aarch64|arm64) PLATFORM_DEPS_NAME="linux-aarch64" ;;
  *) PLATFORM_DEPS_NAME="" ;;
esac

DEPS_ARGS=()
if [ -n "$PLATFORM_DEPS_NAME" ] && [ -d "$DEPS/$PLATFORM_DEPS_NAME" ]; then
  STAGE_ROOT="$ROOT/build/deps-stage"
  rm -rf "$STAGE_ROOT"
  mkdir -p "$STAGE_ROOT/$PLATFORM_DEPS_NAME"
  cp -R "$DEPS/$PLATFORM_DEPS_NAME/." "$STAGE_ROOT/$PLATFORM_DEPS_NAME/"
  DEPS_ARGS=(--add-data "$STAGE_ROOT:deps")
else
  echo "warning: platform dependency directory not found for $(uname -m); tray deps will be installed at runtime" >&2
fi

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "LJM-Java-Manager" \
  --hidden-import plistlib \
  --hidden-import hashlib \
  --hidden-import locale \
  --hidden-import socket \
  --hidden-import stat \
  --add-data "$ASSETS/java.ico:." \
  --add-data "$ASSETS/build/java.png:." \
  ${DEPS_ARGS[@]+"${DEPS_ARGS[@]}"} \
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
