#!/usr/bin/env bash
# Tier 2: HTTP clients — run individually for local development.
# Usage: ./tests/integration/run_tier2_http_clients.sh

TIER_LABEL="Tier 2: HTTP clients"
APPS=(
  "http-clients-app:8089:/test-all"
)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_run_tier.sh"
