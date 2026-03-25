#!/usr/bin/env bash
# Tier 1: Web frameworks — run individually for local development.
# Usage: ./tests/integration/run_tier1_web_frameworks.sh

TIER_LABEL="Tier 1: Web frameworks"
APPS=(
  "fastapi-app:8084:/rolldice"
  "tornado-app:8085:/rolldice"
  "falcon-app:8086:/rolldice"
  "pyramid-app:8087:/rolldice"
  "aiohttp-server-app:8088:/rolldice"
)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_run_tier.sh"
