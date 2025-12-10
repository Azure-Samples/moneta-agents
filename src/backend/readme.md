# Overview
Moneta backend.

The project is managed by pyproject.toml and [uv package manager](https://docs.astral.sh/uv/getting-started/installation/).


## Local execution
For local execution init the .venv environment using [uv package manager](https://docs.astral.sh/uv/getting-started/installation/):

```shell
cd src/backend
uv sync
. ./.venv/bin/activate
uvicorn app:app
```

**OBS!** Environment variables will be read from the AZD env file: $project/.azure/<selected_azd_environment>/.env automatically


## Orchestrator Architecture

The backend supports two orchestrator modes that can be selected via the `USE_FOUNDRY` environment variable:

### Azure OpenAI Mode (Default)
- **`USE_FOUNDRY=false`** (or not set)
- Uses `AzureOpenAIChatClient` with **in-memory agents**
- Agents are created on-the-fly and don't persist between sessions
- Requires `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT_NAME` environment variables
- Orchestrators: `OpenAIBankingOrchestrator`, `OpenAIInsuranceOrchestrator`

### Microsoft Foundry Mode
- **`USE_FOUNDRY=true`** (or `1` or `yes`)
- Uses `AzureAIClient` with **hosted agents** in Microsoft Foundry
- Agents are persistent and visible in the Foundry UI
- Requires `AZURE_AI_PROJECT_ENDPOINT` (or `PROJECT_ENDPOINT`) and `MODEL_DEPLOYMENT_NAME` environment variables
- Orchestrators: `FoundryBankingOrchestrator`, `FoundryInsuranceOrchestrator`

### Orchestrator Files

```
foundry/orchestrators/
├── foundry_banking_orchestrator.py    # Foundry hosted agents for banking
├── foundry_insurance_orchestrator.py  # Foundry hosted agents for insurance
├── open_ai_banking_orchestrator.py    # Azure OpenAI in-memory agents for banking
├── open_ai_insurance_orchestrator.py  # Azure OpenAI in-memory agents for insurance
├── deep_research_orchestrator.py      # Deep research orchestrator
└── custom_span_processor.py           # Tracing utilities
```

### Handler Selection Logic

The `handler.py` automatically selects the appropriate orchestrator based on:
1. `USE_FOUNDRY` environment variable
2. Use case type (`fsi_banking`, `fsi_insurance`, `deep_research`)

```python
# Example: To use Foundry mode
export USE_FOUNDRY=true

# Example: To use Azure OpenAI mode (default)
export USE_FOUNDRY=false
```