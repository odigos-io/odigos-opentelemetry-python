#!/usr/bin/env bash
#
# Extended integration tests — covers all instrumentations beyond the core
# four (flask, django, gunicorn, sqlalchemy) that run.sh tests on every PR.
#
# This script is triggered on-demand via the integration-test-extended
# GitHub Actions workflow. It runs all tiers together for CI efficiency.
#
# For local development you can run individual tiers instead:
#   ./tests/integration/run_tier1_web_frameworks.sh
#   ./tests/integration/run_tier2_http_clients.sh
#   ./tests/integration/run_tier4_databases.sh
#   ./tests/integration/run_tier5_message_brokers.sh
#   ./tests/integration/run_tier6_additional.sh
#
# Usage:  ./tests/integration/run_extended.sh

TIER_LABEL="All extended integration tests"
APPS=(
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
  "pymssql-app:8103:/test"
)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_run_tier.sh"
