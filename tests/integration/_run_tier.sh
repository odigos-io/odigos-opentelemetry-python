#!/usr/bin/env bash
#
# Common runner for integration test tiers.
#
# This script is sourced (not executed directly) by tier-specific runners.
# The sourcing script must set:
#   APPS        — array of "service_name:host_port:test_endpoint" entries
#   TIER_LABEL  — human-readable label, e.g. "Tier 1: Web frameworks"
#
# Example:
#   APPS=("fastapi-app:8084:/rolldice" "tornado-app:8085:/rolldice")
#   TIER_LABEL="Tier 1: Web frameworks"
#   source "$(dirname "${BASH_SOURCE[0]}")/_run_tier.sh"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yaml"
OUTPUT_DIR="$SCRIPT_DIR/output"

READY_TIMEOUT=300
POLL_INTERVAL=5
FLUSH_WAIT=15
TRAFFIC_REQUESTS=1

# Extract docker compose service names from the APPS array
SERVICES=()
for entry in "${APPS[@]}"; do
  IFS=':' read -r svc _ _ <<< "$entry"
  SERVICES+=("$svc")
done

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
echo "── Starting containers ($TIER_LABEL) ────────────────────────────"
docker compose -f "$COMPOSE_FILE" build --no-cache agent "${SERVICES[@]}"
docker compose -f "$COMPOSE_FILE" up -d "${SERVICES[@]}"

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
echo ""
echo "── Verifying traces ─────────────────────────────────────────────"
EXPECTED_SERVICES=()
for entry in "${APPS[@]}"; do
  IFS=':' read -r svc _ _ <<< "$entry"
  EXPECTED_SERVICES+=("$svc")
done

VERIFY_FAIL=false
python3 "$SCRIPT_DIR/verify_extended.py" \
  --traces-file "$OUTPUT_DIR/traces.json" \
  --expected-services "${EXPECTED_SERVICES[@]}" || VERIFY_FAIL=true

# ── 8. Check container logs for Python errors ────────────────────────
echo ""
echo "── Checking container logs for Python errors ────────────────────"
LOG_FAIL=false
for entry in "${APPS[@]}"; do
  IFS=':' read -r svc _ _ <<< "$entry"
  LOGS=$(docker compose -f "$COMPOSE_FILE" logs "$svc" 2>&1)
  TB_COUNT=$(echo "$LOGS" | grep -c "Traceback (most recent call last)" || true)
  DETACH_COUNT=$(echo "$LOGS" | grep -c "Failed to detach context" || true)

  if [ "$TB_COUNT" -gt 0 ] && [ "$TB_COUNT" -gt "$DETACH_COUNT" ]; then
    echo "  FAIL: Python traceback found in $svc"
    echo "$LOGS" | tail -30
    LOG_FAIL=true
  elif [ "$TB_COUNT" -gt 0 ]; then
    echo "  WARN: $svc — OTel context detach warning (non-fatal)"
  else
    echo "  OK: $svc — no tracebacks"
  fi
done

if [ "$VERIFY_FAIL" = true ] || [ "$LOG_FAIL" = true ]; then
  exit 1
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  $TIER_LABEL — all checks passed!"
echo "══════════════════════════════════════════════════════════════════"
