# Insurance CRM Agent

The CRM Insurance Agent handles client insurance data and policy information queries.

## Features

- Retrieves client insurance information by name or ID
- Provides policy details including coverage, effective dates, and benefits
- Summarizes all active policies for a client

## Functions Available

- `load_insurance_client_by_fullname`: Load client by full name
- `load_insurance_client_by_id`: Load client by ID
- `get_client_policy_details`: Get specific policy details

## Data Source

The CRM Insurance Agent uses the customer insurance data from:
`src/data/customer-profiles/customer-insurance.json`

## Usage

```python
from foundry.agents.insurance.crm import create_crm_insurance_agent

agent = await create_crm_insurance_agent(chat_client)
```

## Running Standalone

```bash
cd src/backend
source .venv/bin/activate
python -m foundry.agents.insurance.crm.crm_insurance_agent
```
