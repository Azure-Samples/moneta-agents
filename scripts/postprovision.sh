#!/bin/bash
set -e
eval "$(azd env get-values)"

echo "Running post-provision hook..."

python3 ./scripts/data_load/data_upload.py
python3 ./scripts/data_load/data_indexing.py
python3 ./scripts/data_load/data_upload_customer_profiles.py