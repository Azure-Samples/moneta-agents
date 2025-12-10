#!/bin/bash
set -e

# Update APT cache
sudo apt update

pip install --upgrade pip 
pip install -r src/frontend/requirements.txt 
pip install -r src/backend/requirements.txt

# Install uv, see https://astral.sh for additional information
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export UV_LINK_MODE=copy' >> $HOME/.bashrc
source $HOME/.bashrc

