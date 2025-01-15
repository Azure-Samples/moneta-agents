# Overview
Moneta backend.

The project is managed by pyproject.toml and [uv package manager](https://docs.astral.sh/uv/getting-started/installation/).


## Local execution
For local execution init the .venv environment using [uv package manager](https://docs.astral.sh/uv/getting-started/installation/):

```shell
cd src/backend
uv sync
. ./.venv/bin/actvate
uvicorn app:app
```

**OBS!** Environment variables will be read from the AZD env file: $project/.azure/<selected_azd_environment>/.env automatically