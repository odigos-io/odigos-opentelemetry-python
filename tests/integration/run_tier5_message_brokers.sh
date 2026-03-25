#!/usr/bin/env bash
# Tier 5: Message broker clients — run individually for local development.
# Usage: ./tests/integration/run_tier5_message_brokers.sh

TIER_LABEL="Tier 5: Message brokers"
APPS=(
  "rabbitmq-app:8096:/test"
  "kafka-app:8097:/test"
)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_run_tier.sh"
