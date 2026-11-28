#!/usr/bin/env bash
# Loads the demo ledger (src/main/resources/demo/demo-ledger.sql) into the running Docker database for ONE existing
# user. The backend already does this automatically for the demo users and, when DEMO_DATA_FOR_NEW_USERS=true, for
# every new sign-up; use this script to (re)load it for any other account.
#
#   ./scripts/load-demo-data.sh you@example.com            # the standard demo data (same numbers as the app's mock)
#   ./scripts/load-demo-data.sh you@example.com saver      # another profile: standard, saver, freelancer,
#                                                          # student or family
#
# Running it again replaces that user's accounts, transactions, transfers and budgets; other users are not touched.
set -euo pipefail

cd "$(dirname "$0")/.."
EMAIL="${1:?Usage: ./scripts/load-demo-data.sh you@example.com [standard|saver|freelancer|student|family]}"
PROFILE="${2:-standard}"

env_value() { grep -E "^$1=" .env | tail -1 | cut -d= -f2-; }

{
  echo '\set ON_ERROR_STOP on'
  echo 'BEGIN;'
  cat src/main/resources/demo/demo-ledger.sql
  echo "SELECT pg_temp.demo_load_ledger_for_email(:'email', :'profile') AS transactions_written;"
  echo 'COMMIT;'
} | docker compose exec -T db psql -q -v email="$EMAIL" -v profile="$PROFILE" -U "$(env_value DB_USERNAME)" -d "$(env_value DB_NAME)"
