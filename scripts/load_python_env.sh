#!/bin/sh

echo 'Creating Python virtual environment "scripts/.venv"...'
python -m venv .venv

echo 'Installing dependencies from "requirements.txt" into virtual environment (in quiet mode)...'
# .venv/bin/python -m pip --quiet --disable-pip-version-check install -r scripts/requirements.txt
./.venv/bin/python -m pip --disable-pip-version-check install -r scripts/requirements.txt
