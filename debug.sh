#!/usr/bin/env bash
# debug.sh — host-side watcher/build script for macOS
set -euo pipefail

# 1) Ensure fswatch is installed
if ! command -v fswatch >/dev/null; then
  echo "⚠️  fswatch is required. Install with: brew install fswatch"
  exit 1
fi

IMAGE_NAME="local-pypi-server"
CONTAINER_NAME="pypi-server"
PORT=8080

# 2) Create a fresh temp dir for dist files
DIST_VOL=./dist
echo "ℹ️  Using host volume: $DIST_VOL"

# 3) Build functions
build_packages() {
  rm -rf ./dist/* || true
  make build
}

# 4) Start the server (once)
start_server() {
  echo "🚀 Starting PyPI server container (mount: $DIST_VOL → /app/dist)..."
  docker build -t "$IMAGE_NAME" -f debug.Dockerfile .
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker run -d \
    --rm \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8080" \
    -v "$DIST_VOL":/app/dist \
    "$IMAGE_NAME"
}

# 5) Watch for changes & only rebuild+sync
watch_and_sync() {
  echo "👀 Watching for file changes (ignoring all dist/ dirs)… (Ctrl-C to stop)"
  fswatch -r \
    --exclude '.*/\.git/.*' \
    --exclude '.*odigos_.*' \
    --exclude '.*/dist.*' \
    . | while read -r path; do
      echo "🔄 Change detected at $(date '+%H:%M:%S'): $path"
      build_packages
    done
}

# === Main ===
build_packages
start_server
# watch_and_sync
