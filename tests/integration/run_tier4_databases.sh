#!/usr/bin/env bash
# Tier 4: Database clients — run individually for local development.
# Usage: ./tests/integration/run_tier4_databases.sh

TIER_LABEL="Tier 4: Database clients"
APPS=(
  "redis-app:8090:/test"
  "postgres-app:8091:/test"
  "mysql-app:8092:/test"
  "mongo-app:8093:/test"
  "memcached-app:8094:/test"
  "elasticsearch-app:8095:/test"
)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_run_tier.sh"
