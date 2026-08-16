#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$ROOT/src"
ASSETS="$ROOT/assets"
DEPS="$ROOT/vendor/deps"
cd "$ROOT"

# vendor/deps carries wheels for every platform; only the directory matching
# this build machine may go into the app bundle, otherwise one package would
# ship components for all three operating systems.
case "$(uname -m)" in
  arm64|aarch64) PLATFORM_DEPS_NAME="macos-arm64" ;;
  x86_64|amd64) PLATFORM_DEPS_NAME="macos-x86_64" ;;
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
  --windowed \
  --name "LJM-Java-Manager" \
  --icon "$ASSETS/build/java.icns" \
  --hidden-import plistlib \
  --hidden-import hashlib \
  --hidden-import locale \
  --hidden-import socket \
  --hidden-import stat \
  --add-data "$ASSETS/java.ico:." \
  ${DEPS_ARGS[@]+"${DEPS_ARGS[@]}"} \
  "$SRC/LJM.pyw"

chmod +x "$ROOT/dist/LJM-Java-Manager.app/Contents/MacOS/LJM-Java-Manager"

echo "macOS build finished: $ROOT/dist/LJM-Java-Manager.app"
