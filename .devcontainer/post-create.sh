#!/usr/bin/env bash
set -euo pipefail
[[ ${DEBUG-} =~ ^1|yes|true$ ]] && set -o xtrace

# Update the package list and upgrade all packages
sudo apt update
sudo apt upgrade -y

# Install UV and sync the configuration (installs required python packages)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Staship prompt
curl -sS https://starship.rs/install.sh | sh -s -- -y
echo 'eval "$(starship init bash)"' >> ~/.bashrc
source ~/.bashrc

printf "\n\n\033[1m✅ DevContainer for Moneta Agents was successfully created!\033[0m\n\n"
printf "Next steps: \n"
printf "  - Start hacking right away! 🚀\n"
printf "  - Add python dependencies to pyproject.yaml by running 'uv add <package>'\n"
printf "  - See https://docs.astral.sh/uv/ for more information\n"