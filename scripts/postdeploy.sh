#!/bin/bash
set -e
# eval "$(azd env get-values)"

echo "Running post-deploy hook..."

.venv/bin/python ./scripts/data_load/setup_cosmosdb.py
.venv/bin/python ./scripts/data_load/setup_aisearch.py