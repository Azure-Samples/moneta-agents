# Overview
Moneta backend.

The project is managed by pyproject.toml and [uv package manager](https://docs.astral.sh/uv/getting-started/installation/).


## Local execution
For local execution init the .venv environment using [uv package manager](https://docs.astral.sh/uv/getting-started/installation/):

```shell
cd src/backend
uv sync
. ./.venv/bin/actvate
python app.py
```

**OBS!** Environment variables will be read from the AZD env file: $project/.azure/<selected_azd_environment>/.env automatically

## Azure Container Apps
Dockerised deployment in Azure Container Apps dependencies are sourced from requirements.txt

If pyproject.toml is updated, manually or by using `uv add`, requirements.txt must be regenerated from pyproject.toml:

```shell
uv pip compile ../../pyproject.toml --no-deps |\
    grep -v '# via' |\
    grep -v ipykernel > requirements.txt 
```