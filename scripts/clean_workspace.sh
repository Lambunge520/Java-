#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

remove_path() {
  local target="$1"
  [[ -e "$target" ]] || return 0

  local resolved
  resolved="$(cd "$(dirname "$target")" && pwd)/$(basename "$target")"
  case "$resolved" in
    "$ROOT"/*) rm -rf "$resolved" ;;
    *) echo "Refusing to remove path outside repository: $resolved" >&2; exit 1 ;;
  esac
}

remove_path "$ROOT/build"
remove_path "$ROOT/dist"
remove_path "$ROOT/deps_wheels_tmp"
remove_path "$ROOT/release-assets"

find "$ROOT" -path "$ROOT/.git" -prune -o -type d -name "__pycache__" -exec rm -rf {} +
find "$ROOT" -path "$ROOT/.git" -prune -o -type f \( \
  -name "*.pyc" -o \
  -name "*.pyo" -o \
  -name "*.spec" -o \
  -name "*.log" -o \
  -name "*.tmp" -o \
  -name "*.new" -o \
  -name "ljm_headless_result.json" -o \
  -name "headless_test_result*.json" -o \
  -name "LJM-Java-Manager*.zip" -o \
  -name "LJM-Java-Manager*.tar.gz" -o \
  -name "LJM-Java-Manager*.tgz" -o \
  -name "LJM-Java-Manager*.exe" -o \
  -name "SHA256SUMS*.txt" \
\) -exec rm -f {} +

echo "Workspace cleanup finished: $ROOT"
