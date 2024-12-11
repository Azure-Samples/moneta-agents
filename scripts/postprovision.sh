#!/bin/bash
set -e
eval "$(azd env get-values)"

echo "Running post-provision hook..."

.venv/bin/python ./scripts/data_load/data_upload.py
.venv/bin/python ./scripts/data_load/data_indexing.py
.venv/bin/python ./scripts/data_load/data_upload_customer_profiles.py