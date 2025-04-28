#!/usr/bin/env bash
# debug.sh — host-side watcher/build script for macOS
set -euo pipefail

# 1) Detect python binary
if command -v python >/dev/null 2>&1; then
  PYTHON=python
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "❌ Error: neither python nor python3 found in PATH" >&2
  exit 1
fi

# 2) Ensure fswatch is installed
if ! command -v fswatch >/dev/null; then
  echo "⚠️  fswatch is required. Install with: brew install fswatch"
  exit 1
fi

IMAGE_NAME="local-pypi-server"
CONTAINER_NAME="pypi-server"
PORT=8080

# 3) Create a fresh temp dir for dist files
DIST_VOL=$(mktemp -d /tmp/pypi-dist.XXXX)
echo "ℹ️  Using host volume: $DIST_VOL"

# 4) Build functions
build_packages() {
  echo "🔧 Building patched instrumentations..."
  make build-instrumentations 2>&1 > /dev/null

  echo "📦 Building odigos-opentelemetry-python wheel..."
  $PYTHON -m build
}

sync_to_volume() {
  echo "📂 Syncing dist/ → $DIST_VOL"
  rsync -a --delete dist/ "$DIST_VOL"/
  echo "📂 Done syncing dist/ → $DIST_VOL"
}

# 5) Start the server (once)
start_server() {
  echo "🚀 Starting PyPI server container (mount: $DIST_VOL → /app/dist)..."
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8080" \
    -v "$DIST_VOL":/app/dist \
    "$IMAGE_NAME"
}

# 6) Watch for changes & only rebuild+sync, but ignore dist/ and temp volume
watch_and_sync() {
  echo "👀 Watching for file changes (ignoring all dist/ dirs)… (Ctrl-C to stop)"
  fswatch -r \
    --exclude '.*/\.git/.*' \
    --exclude '.*/dist' \
    --exclude '.*odigos_.*' \
    . | while read -r path; do
      echo "🔄 Change detected at $(date '+%H:%M:%S'): $path"
      build_packages
      sync_to_volume
    done
}

# === Main ===
# build_packages
sync_to_volume
start_server
watch_and_sync
