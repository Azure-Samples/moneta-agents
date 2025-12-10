# Insurance Policies Agent

The Policies Agent provides insurance policy information and product research insights using Azure AI Search.

## Features

- Searches insurance policy documents using semantic search
- Provides coverage details, benefits, and policy terms
- Summarizes key policy features and options

## Environment Variables Required

```
AI_SEARCH_ENDPOINT=<your-ai-search-endpoint>
AI_SEARCH_INS_INDEX_NAME=<your-insurance-index-name>
AI_SEARCH_INS_SEMANTIC_CONFIGURATION=<semantic-configuration-name>
AI_SEARCH_VECTOR_FIELD_NAME=contentVector
```

## Usage

```python
from foundry.agents.insurance.policies import create_policies_agent

agent = await create_policies_agent(chat_client)
```

## Running Standalone

```bash
cd src/backend
source .venv/bin/activate
python -m foundry.agents.insurance.policies.policies_agent
```
