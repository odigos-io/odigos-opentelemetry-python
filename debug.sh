#!/usr/bin/env bash
# debug.sh — host-side watcher/build script for macOS
set -euo pipefail

# detect python binary (assume `python` is Python 3 if it exists)
if command -v python >/dev/null 2>&1; then
  PYTHON=python
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "❌ Error: neither python nor python3 found in PATH" >&2
  exit 1
fi

IMAGE_NAME="local-pypi-server"
CONTAINER_NAME="pypi-server"
PORT=8080

# ensure fswatch is installed
if ! command -v fswatch >/dev/null; then
  echo "⚠️  fswatch is required. Install with: brew install fswatch"
  exit 1
fi

build_packages() {
  echo "🔧 Building patched instrumentations..."
  make build-instrumentations

  echo "📦 Building odigos-opentelemetry-python wheel..."
  $PYTHON -m build
}

build_image() {
  echo "🐳 Building Docker image..."
  docker build -t "$IMAGE_NAME" -f debug.Dockerfile .
}

start_server() {
  echo "🚀 (Re)starting PyPI server container..."
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker run --rm -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:8080" \
    -v "$(pwd)/dist":/app/dist \
    "$IMAGE_NAME"
}

watch_and_reload() {
  echo "👀 Watching for file changes… (Ctrl-C to stop)"
  fswatch -o . | while read -r _; do
    echo "------ Change detected at $(date '+%H:%M:%S') ------"
    build_packages
    build_image
    start_server
  done
}

# === main ===
build_packages
build_image
start_server
watch_and_reload
