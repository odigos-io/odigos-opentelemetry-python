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
  # Original apps
  "flask-app:8081:/rolldice"
  "pythongunicorn:8000:/sub/home"
  "django-app:8082:/rolldice"
  "sqlalchemy-app:8083:/rolldice"
  # Tier 1: Web frameworks
  "fastapi-app:8084:/rolldice"
  "tornado-app:8085:/rolldice"
  "falcon-app:8086:/rolldice"
  "pyramid-app:8087:/rolldice"
  "aiohttp-server-app:8088:/rolldice"
  # Tier 2: HTTP clients
  "http-clients-app:8089:/test-all"
  # Tier 4: Database clients
  "redis-app:8090:/test"
  "postgres-app:8091:/test"
  "mysql-app:8092:/test"
  "mongo-app:8093:/test"
  "memcached-app:8094:/test"
  "elasticsearch-app:8095:/test"
  # Tier 5: Message broker clients
  "rabbitmq-app:8096:/test"
  "kafka-app:8097:/test"
  # Tier 6: Additional instrumentations
  "tortoiseorm-app:8098:/test"
  "grpc-app:8099:/test"
  "celery-app:8100:/test"
  "boto-app:8101:/test"
  "cassandra-app:8102:/test"
  "pymssql-app:8103:/test"
)

READY_TIMEOUT=300           # max seconds to wait for all apps to become reachable
POLL_INTERVAL=5             # seconds between readiness polls
FLUSH_WAIT=15               # seconds to wait for spans to flush
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
make build

# Copy instrumentation wheels into dist/ so Dockerfile.agent can find them
for inst_dir in instrumentations/*/dist; do
  [ -d "$inst_dir" ] && cp "$inst_dir"/* dist/
done

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

# ── 4. Poll until every app endpoint is reachable ────────────────────
echo ""
echo "── Waiting for all services to become ready (timeout ${READY_TIMEOUT}s) ──"
START_TS=$(date +%s)

PENDING=("${APPS[@]}")
TOTAL=${#APPS[@]}
NUM_READY=0

while [ ${#PENDING[@]} -gt 0 ]; do
  ELAPSED=$(( $(date +%s) - START_TS ))
  if [ "$ELAPSED" -ge "$READY_TIMEOUT" ]; then
    echo ""
    echo "FAIL: Timed out after ${READY_TIMEOUT}s. Still waiting on:"
    for entry in "${PENDING[@]}"; do
      IFS=':' read -r svc port endpoint <<< "$entry"
      echo "  - $svc (http://localhost:$port$endpoint)"
      echo "    ── container status ──"
      docker compose -f "$COMPOSE_FILE" ps "$svc" 2>&1 | tail -3
      echo "    ── last 15 log lines ──"
      docker compose -f "$COMPOSE_FILE" logs --tail=15 "$svc" 2>&1
    done
    exit 1
  fi

  STILL_PENDING=()
  for entry in "${PENDING[@]}"; do
    IFS=':' read -r svc port endpoint <<< "$entry"
    if curl -sf --max-time 15 "http://localhost:$port$endpoint" > /dev/null 2>&1; then
      NUM_READY=$((NUM_READY + 1))
      echo "  ready: $svc  (${ELAPSED}s, $NUM_READY/$TOTAL)"
    else
      STILL_PENDING+=("$entry")
    fi
  done
  if [ ${#STILL_PENDING[@]} -eq 0 ]; then
    PENDING=()
  else
    PENDING=("${STILL_PENDING[@]}")
  fi

  if [ ${#PENDING[@]} -gt 0 ]; then
    sleep "$POLL_INTERVAL"
  fi
done

ELAPSED=$(( $(date +%s) - START_TS ))
echo "  All $TOTAL services ready in ${ELAPSED}s"

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

VERIFY_FAIL=false
python3 "$SCRIPT_DIR/verify.py" \
  --traces-file "$OUTPUT_DIR/traces.json" \
  --expected-services "${EXPECTED_SERVICES[@]}" || VERIFY_FAIL=true

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

if [ "$VERIFY_FAIL" = true ] || [ "$LOG_FAIL" = true ]; then
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  All integration tests passed!"
echo "══════════════════════════════════════════════════════════════════"
