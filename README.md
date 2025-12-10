# Moneta - an AI-Agentic Assistant for Insurance and Banking

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/albertaga27/aoai-fsi-empowering-advisory-agentic) [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/albertaga27/aoai-fsi-empowering-advisory-agentic)

Moneta is an AI-powered assistant designed to empower insurance and banking advisors. This Solution Accelerator provides a chat interface where advisors can interact with various AI agents specialized in different domains such as insurance policies, CRM, product information, funds, CIO insights, and news.

## 🚀 Agent Framework & Azure AI Foundry (optional)

Moneta uses the **Microsoft Agent Framework** to orchestrate Agents:

* [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) - Multi-agent orchestration with HandoffBuilder pattern
* [Azure AI Foundry](https://ai.azure.com/) - Native hosted agents with versioning support

### Key Architecture Features

- **HandoffBuilder Pattern**: Coordinator agent routes requests to specialist agents (CRM, CIO, Funds, News, Policies)
- **Dual Mode Support**: Run with standard Azure OpenAI agents OR optionally with Azure AI Foundry hosted agents
- **Conversation Memory**: Full conversation history is maintained across API calls via CosmosDB
- **OpenTelemetry Tracing**: Built-in observability with Azure Application Insights integration
- **Session-Level Tracing**: Custom spans for conversation turns and agent handoffs

### Agent Hosting Modes

Moneta supports two agent hosting modes:

| Mode | Description | Command |
|------|-------------|--------|
| **Azure OpenAI** (default) | Agents run in-memory using `AzureOpenAIChatClient`. Fast startup, no persistence. | `python -m foundry.orchestrators.foundry_banking_orchestrator` |
| **Azure AI Foundry** (optional) | Agents are persisted to Azure AI Foundry with versioning. Visible in Foundry UI. | `python -m foundry.orchestrators.foundry_banking_orchestrator --foundry --new` |

Use the ENV variable USE_FOUNDRY= True or False


### Foundry Handoff Pattern - Key Insight

> **⚠️ Critical Architecture Note for Foundry-Hosted Agents**
> 
> The key insight is that Agent Framework Handoff: `auto_register_handoff_tools(True)` needs to work at runtime, but the Foundry agent's model already has the handoff tool schemas baked in at creation time. The problem is the **HandoffBuilder can't inject the actual handoff functions into Foundry agents because they're hosted remotely**!

The callable handoff tools:
- Match the schema pattern used by HandoffBuilder: `handoff_to_<agent_name>`
- Return a deterministic acknowledgement like `"Handoff to <agent_name>"`
- Are bound locally to the coordinator's ChatAgent wrapper

**For Foundry-hosted agents, you need BOTH:**
1. **Tool schemas** (`FunctionTool`) - Registered with Foundry so the model knows about them
2. **Callable functions** (`@ai_function`) - Bound locally so the framework can execute them


### Solution Screenshots

The following screenshots demonstrate the agents running:

#### Moneta Frontend - Orchestrator and sub agents responses

![Moneta Frontend](src/backend/testing/Screenshot%202025-12-10%20110948.png)

This screenshot shows the `ins-coordinator` agent performing intent recognition and invoking the appropriate sub-agents. 

#### Tracing - Full Agent Flow

![Tracing Handoff](src/backend/testing/Screenshot%202025-12-10%20111045.png)

This screenshot shows the **specialist agent's response** in the trace in Application Insights. After the handoff, the `ins-crm-agent` executes its tools (like `get_customer_insurance_data`) to fetch John Doe's policy information and returns the response. The trace captures the entire conversation flow, tool executions, and the final response sent back to the user.

#### Tracing - AI Foundry (new)

![AI Foundry (new)](src/backend/testing/Screenshot%202025-12-10%20111134.png)

This screenshot shows the **orchestrator banking agent** in the Monitor section of the new Foundry UI. Traces are sourced from the Application Insights (Connected resource to Foundry project).



## Prerequisites

* Docker
* [uv](https://docs.astral.sh/uv/getting-started/installation/) - Python package manager
* Python 3.12
* Azure CLI (logged in)
* Azure AI Foundry project (for hosted agents)

## Features

- **Microsoft Agent Framework**: Multi-agent orchestration with HandoffBuilder pattern
- **Azure AI Foundry Integration**: Optional hosted agents with versioning support
- Multi-Use Case Support: Switch between insurance and banking use cases
- Agent Collaboration: Coordinator routes to specialists who collaborate to provide answers
- Azure AD Authentication: Secure login with Microsoft Azure Active Directory
- Conversation History: Access and continue previous conversations with full context

## Implementation Details
- Python 3.12 or higher
- **Microsoft Agent Framework** with HandoffBuilder for multi-agent orchestration
- **Azure OpenAI** for agent inference (default mode)
- **Azure AI Foundry** for optional hosted agents with versioning and persistence
- Streamlit (frontend app - chatGPT style with conversation segregation and memory)
- FastAPI (backend API with async support)
- Microsoft Authentication Library (MSAL - if using authentication - optional)
- Azure AD application registration (if using authentication - optional)
- An Azure Container App hosting backend API endpoint
- CosmosDB to store user conversations and history
- Azure Application Insights for OpenTelemetry tracing

## Use Cases

### Insurance

Uses the **HandoffBuilder** pattern with a coordinator that routes to specialist agents:

| Agent Name | Description |
|------------|-------------|
| `ins-coordinator` | Routes user requests to appropriate specialist agents |
| `ins-crm-agent` | Fetches client insurance information and policy data from CRM (simulated) |
| `ins-policies-agent` | Vector search with AI Search on insurance policy documents and product information |

### Banking 

Uses the **HandoffBuilder** pattern with a coordinator that routes to specialist agents:

| Agent Name | Description |
|------------|-------------|
| `bank-coordinator` | Routes user requests to appropriate specialist agents |
| `bank-crm-agent` | Fetches client information and portfolio data from CRM (simulated) |
| `bank-funds-agent` | Vector search with AI Search on funds and ETF factsheets |
| `bank-cio-agent` | Vector search with AI Search on in-house investment views and recommendations |
| `bank-news-agent` | RSS online feed search on stock news for portfolio positions |

> **Note**: Agent names use hyphens (not underscores) to comply with Azure AI Foundry naming requirements: alphanumeric characters and hyphens only, max 63 characters.

All agents can optionally be persisted to **Azure AI Foundry** with automatic versioning using the `--foundry --new` flags.


## Project structure

- src
  - backend
    - foundry
      - agents
        - banking # Banking agent definitions and functions
          - cio/ # CIO agent with AI Search functions
          - crm/ # CRM agent with client data functions
          - funds/ # Funds agent with AI Search functions
          - news/ # News agent with RSS feed functions
        - insurance # Insurance agent definitions and functions
          - crm/ # CRM Insurance agent with client data functions
          - policies/ # Policies agent with AI Search functions
        - agent_management.py # Agent CRUD operations for Foundry
        - tool_schema_utils.py # Utilities for tool schema generation
      - orchestrators
        - foundry_banking_orchestrator.py # Banking orchestrator with HandoffBuilder
        - foundry_insurance_orchestrator.py # Insurance orchestrator with HandoffBuilder
    - app.py # FastAPI backend exposing API

  - frontend
    - app.py # Streamlit app

  - data
    - ai-search-index
      - cio-index
      - funds-index
      - ins-index
    - customer-profiles

- infra
  - bicep files
  - infra modules


### Azure deployment (automated)

To configure, follow these steps:

1. Make sure you AZ CLI is logged in in the right tenant. Optionally:

    ```shell
    az login --tenant your_tenant.onmicrosoft.com
    ```

1. Create a new azd environment:

    ```shell
    azd env new
    ```

    This will create a folder under `.azure/` in your project to store the configuration for this deployment. You may have multiple azd environments if desired.

1. Set the `AZURE_AUTH_TENANT_ID` azd environment variable to the tenant ID you want to use for Entra authentication:

    ```shell
    azd env set AZURE_AUTH_TENANT_ID $(az account show --query tenantId -o tsv)
    ```

1. Login to the azd CLI with the Entra tenant ID:

    ```shell
    azd auth login --tenant-id $(azd env get-value AZURE_AUTH_TENANT_ID)
    ```

1. Proceed with AZD deployment:

    ```shell
    azd up
    ```

### Data indexing (optional)

Demo data is NOT loaded with the `azd up` process automatically.

If you want to provide AI Search services and load demo data into indexes for the banking and insurance agents
you can do it by running:
```shell
azd hooks run postdeploy
```

Indexes are sourced from 'src/data/ai-search-index' folder.
Each subfolder of the data folder will be a seperate index. 

Customer profiles are sourced from 'src/data/customer-profiles'.
Each subfolder of the data folder will be get a seperate index. 

**OBS!** If you deploy from WSL mounted path, the postdeploy data init might fail. Please consider rerunning from WSL native path location.


### Running the App locally - BACKEND

The python project is managed by `pyproject.toml` and the [uv package manager](https://docs.astral.sh/uv/getting-started/installation/).
Install uv prior executing.

To run locally:

Mind the `sample.env` file - by default the application will try to read AZD environment variables and falls back on `.env` only when it does not find one.

Activate the `.venv` virtual environment or run the binary directly:

```shell
cd src/backend
uv sync --prerelease=allow
source .venv/bin/activate
uvicorn app:app --port 8000
```

**Note**: The `--prerelease=allow` flag is required for the agent-framework package.

### Running the App locally - FRONTEND

The python project is managed by pyproject.toml and [uv package manager](https://docs.astral.sh/uv/getting-started/installation/).
Install uv prior executing.

To run locally:

mind the sample.env file - by default the application will try to read AZD environment configuration and falls on .env only when it does not find one.

**Key Environment Variables for Agent Framework:**
```shell
PROJECT_ENDPOINT=https://your-foundry-project.services.ai.azure.com/api/projects/your-project
MODEL_DEPLOYMENT_NAME=gpt-4o-mini
HANDLER_TYPE=foundry_banking
APPLICATIONINSIGHTS_CONNECTION_STRING=your-connection-string
```

**OBS!** Activate .venv or run the binary directly.

```shell
cd src/frontend
uv sync
./.venv/bin/streamlit run app.py
```

### Usage

1. **Select Use Case**: Choose between `fsi_insurance` or `fsi_banking` from the sidebar
2. **Start a Conversation**: Click "Start New Conversation" or select an existing one
3. **Chat**: Use the chat input to ask questions. Predefined questions are available in a dropdown
4. **Agents Online**: View the available agents for the selected use case
5. **Chat Histories**: View and reload your past conversations
