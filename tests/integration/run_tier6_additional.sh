#!/usr/bin/env bash
# Tier 6: Additional instrumentations — run individually for local development.
# Usage: ./tests/integration/run_tier6_additional.sh

TIER_LABEL="Tier 6: Additional instrumentations"
APPS=(
  "tortoiseorm-app:8098:/test"
  "grpc-app:8099:/test"
  "celery-app:8100:/test"
  "boto-app:8101:/test"
  "pymssql-app:8103:/test"
)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_run_tier.sh"
