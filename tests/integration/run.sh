#!/usr/bin/env bash
#
# Builds the package from the current tree, spins up sample apps with the
# OTel Collector via a shared instrumentation volume (replicating the
# odiglet init-container pattern), sends traffic, and verifies that spans
# arrive and no Python errors occur.
#
# Usage:  ./tests/integration/run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yaml"
OUTPUT_DIR="$SCRIPT_DIR/output"

# ── App registry ─────────────────────────────────────────────────────
# Format: "service_name:host_port:test_endpoint"
# To add a new app, append a line here and add its service to
# docker-compose.yaml. No /health endpoint required.
APPS=(
  "flask-app:8081:/rolldice"
  "pythongunicorn:8000:/sub/home"
  "django-app:8082:/rolldice"
  "sqlalchemy-app:8083:/rolldice"
)

STARTUP_WAIT=30             # seconds to wait for containers to start
FLUSH_WAIT=10               # seconds to wait for spans to flush
TRAFFIC_REQUESTS=1          # number of requests per app endpoint

# ── Cleanup on exit ──────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "── Cleaning up ────────────────────────────────────────────────"
  docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

# ── 1. Build wheels ──────────────────────────────────────────────────
echo "── Building wheels ──────────────────────────────────────────────"
cd "$REPO_ROOT"
python3 -m pip install --quiet build 2>/dev/null || true
rm -rf dist/
python3 -m build

echo "  Wheels in dist/:"
ls -1 dist/*.whl

# ── 2. Prepare output directory ──────────────────────────────────────
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR/traces.json"
touch "$OUTPUT_DIR/traces.json"
chmod 777 "$OUTPUT_DIR" "$OUTPUT_DIR/traces.json"

# ── 3. Build and start containers ───────────────────────────────────
echo ""
echo "── Starting containers ──────────────────────────────────────────"
docker compose -f "$COMPOSE_FILE" build --no-cache
docker compose -f "$COMPOSE_FILE" up -d

# ── 4. Wait for containers to be up ─────────────────────────────────
echo ""
echo "── Waiting ${STARTUP_WAIT}s for services to start ───────────────"
sleep "$STARTUP_WAIT"

# Verify containers are still running (didn't crash on startup)
for entry in "${APPS[@]}"; do
  IFS=':' read -r svc _ _ <<< "$entry"
  if ! docker compose -f "$COMPOSE_FILE" ps --status running "$svc" | grep -q "$svc"; then
    echo "FAIL: $svc is not running"
    echo ""
    echo "── Container logs ($svc) ──"
    docker compose -f "$COMPOSE_FILE" logs "$svc"
    exit 1
  fi
  echo "  $svc is running"
done

# ── 5. Send traffic ─────────────────────────────────────────────────
echo ""
echo "── Sending test traffic ─────────────────────────────────────────"
for entry in "${APPS[@]}"; do
  IFS=':' read -r svc port endpoint <<< "$entry"
  echo "  $svc -> http://localhost:$port$endpoint (×${TRAFFIC_REQUESTS})"
  for _ in $(seq 1 "$TRAFFIC_REQUESTS"); do
    curl -sf "http://localhost:$port$endpoint" > /dev/null || true
    sleep 0.3
  done
done

# ── 6. Wait for span flush ──────────────────────────────────────────
echo ""
echo "── Waiting ${FLUSH_WAIT}s for spans to flush ────────────────────"
sleep "$FLUSH_WAIT"

# ── 7. Verify traces ────────────────────────────────────────────────
# Runs verify.py which parses the collector's file-exporter output
# (OTLP JSON lines) and asserts:
#   - At least one span was received
#   - Every expected service sent spans
#   - No spans carry an ERROR status
echo ""
echo "── Verifying traces ─────────────────────────────────────────────"
EXPECTED_SERVICES=()
for entry in "${APPS[@]}"; do
  IFS=':' read -r svc _ _ <<< "$entry"
  EXPECTED_SERVICES+=("$svc")
done

python3 "$SCRIPT_DIR/verify.py" \
  --traces-file "$OUTPUT_DIR/traces.json" \
  --expected-services "${EXPECTED_SERVICES[@]}"

# ── 8. Check container logs for Python errors ────────────────────────
echo ""
echo "── Checking container logs for Python errors ────────────────────"
LOG_FAIL=false
for entry in "${APPS[@]}"; do
  IFS=':' read -r svc _ _ <<< "$entry"
  LOGS=$(docker compose -f "$COMPOSE_FILE" logs "$svc" 2>&1)
  if echo "$LOGS" | grep -q "Traceback (most recent call last)"; then
    echo "  FAIL: Python traceback found in $svc"
    echo "$LOGS" | tail -30
    LOG_FAIL=true
  else
    echo "  OK: $svc — no tracebacks"
  fi
done

if [ "$LOG_FAIL" = true ]; then
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  All integration tests passed!"
echo "══════════════════════════════════════════════════════════════════"
