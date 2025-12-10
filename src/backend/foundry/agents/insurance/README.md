# Insurance Agents

This folder contains the insurance-related agents for the Moneta Agentic Advisory system.

## Structure

```
insurance/
├── __init__.py
├── README.md
├── crm/
│   ├── __init__.py
│   ├── crm_insurance_agent.py
│   ├── crm_insurance_functions.py
│   └── README.md
└── policies/
    ├── __init__.py
    ├── policies_agent.py
    ├── policies_functions.py
    └── README.md
```

## Agents

### 1. Policies Agent (`policies/policies_agent.py`)

The Policies Agent provides insurance policy information and product research insights using Azure AI Search.

**Features:**
- Searches insurance policy documents using semantic search
- Provides coverage details, benefits, and policy terms
- Summarizes key policy features and options

**Environment Variables Required:**
```
AI_SEARCH_ENDPOINT=<your-ai-search-endpoint>
AI_SEARCH_INS_INDEX_NAME=<your-insurance-index-name>
AI_SEARCH_INS_SEMANTIC_CONFIGURATION=<semantic-configuration-name>
AI_SEARCH_VECTOR_FIELD_NAME=contentVector
```

**Usage:**
```python
from foundry.agents.insurance.policies import create_policies_agent

agent = await create_policies_agent(chat_client)
```

### 2. CRM Insurance Agent (`crm/crm_insurance_agent.py`)

The CRM Insurance Agent handles client insurance data and policy information queries.

**Features:**
- Retrieves client insurance information by name or ID
- Provides policy details including coverage, effective dates, and benefits
- Summarizes all active policies for a client

**Functions Available:**
- `load_insurance_client_by_fullname`: Load client by full name
- `load_insurance_client_by_id`: Load client by ID
- `get_client_policy_details`: Get specific policy details

**Usage:**
```python
from foundry.agents.insurance.crm import create_crm_insurance_agent

agent = await create_crm_insurance_agent(chat_client)
```

## Data Source

The CRM Insurance Agent uses the customer insurance data from:
`src/data/customer-profiles/customer-insurance.json`

## Running Standalone

Each agent can be run standalone for testing:

```bash
cd src/backend
source .venv/bin/activate
python -m foundry.agents.insurance.policies.policies_agent
# or
python -m foundry.agents.insurance.crm.crm_insurance_agent
```
