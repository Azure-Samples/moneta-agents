# CRM Agent Implementation

This implementation provides a CRM agent using Azure AI Foundry Agent Service libraries that can process user requests about client data and client portfolios.

## 📁 Directory Structure

```
08-moneta-agents-banking/
├── .env                      # Environment variables
├── pyproject.toml           # Python project dependencies
├── requirements.txt         # Alternative dependency file
└── agents/
    └── crm/                 # CRM Agent Package
        ├── __init__.py      # Package initialization
        ├── crm_agent.py     # Main CRM agent implementation
        ├── crm_functions.py # CRM data access functions
        ├── client_sample.json # Sample client data
        ├── test_crm_functions.py # Unit tests
        └── README.md        # This documentation
```

## 🏗️ Architecture

The CRM agent consists of several components:

- **`crm_agent.py`**: Main agent implementation using Azure AI Agents
- **`crm_functions.py`**: CRM data access functions
- **`client_sample.json`**: Sample client data (simulating CRM database)
- **`test_crm_functions.py`**: Unit tests for CRM functions
- **`__init__.py`**: Package initialization for modular imports
- **`README.md`**: This documentation

## 🚀 Features

- **Secure Authentication**: Uses DefaultAzureCredential for Azure authentication
- **Function Calling**: Automatic function calling enabled for CRM data access
- **Agent Lifecycle Management**: Checks for existing agents before creating new ones
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Data Validation**: Validates client IDs and names before processing
- **Conversation History**: Maintains and displays conversation logs
- **Resource Management**: Smart cleanup with user control over agent persistence

## 📋 Prerequisites

1. **Azure AI Project**: You need an Azure AI project with deployed models
2. **Environment Variables**: Configure the following in your `.env` file:
   ```
   PROJECT_ENDPOINT="your_project_endpoint"
   MODEL_DEPLOYMENT_NAME="gpt-4o"
   ```
3. **Azure Authentication**: Ensure you're authenticated to Azure (via Azure CLI or other methods)

## 🛠️ Installation

1. Navigate to the project directory:
   ```bash
   cd /home/aga/azureai/ai-agents/Labfiles/08-moneta-agents-banking
   ```

2. Install dependencies:
   ```bash
   uv sync --prerelease=allow
   ```

3. Configure environment variables in `.env` file

4. Test the CRM functions:
   ```bash
   cd agents/crm
   python test_crm_functions.py
   ```

## 🎯 Usage

### Running the CRM Agent

```bash
cd agents/crm
python crm_agent.py
```

### Sample Interactions

The agent responds to queries about client data and portfolios. Here are example interactions:

**Example 1: Query by Client Name**
```
User: What is Pete Mitchell's portfolio performance?
Agent: Based on the CRM data for Pete Mitchell (Client ID: 123456), his portfolio performance is:
- Year-to-Date: 12.3%
- Since Inception: 22.3%
- Inception Date: 12/07/2015
```

**Example 2: Query by Client ID**
```
User: Show me the investment profile for client 123456
Agent: Client 123456 (Pete Mitchell) has the following investment profile:
- Risk Profile: Aggressive
- Investment Objectives: Growth
- Investment Horizon: Long-term
```

**Example 3: Portfolio Details**
```
User: What stocks does Pete Mitchell hold?
Agent: Pete Mitchell's portfolio includes the following positions:
- Microsoft Corp (MSFT): 200 units at $350 average cost
- NVIDIA Corp (NVDA): 150 units at $150 average cost
- Apple Inc (AAPL): 100 units at $90 average cost
[... additional holdings ...]
```

## 🔧 CRM Functions

### `load_from_crm_by_client_fullname(client_fullname: str)`

Loads client data by full name.

**Parameters:**
- `client_fullname`: The full name of the client (e.g., "Pete Mitchell")

**Returns:**
- JSON string with client data or error message

### `load_from_crm_by_client_id(client_id: str)`

Loads client data by client ID.

**Parameters:**
- `client_id`: The client ID (e.g., "123456")

**Returns:**
- JSON string with client data or error message

## 📊 Sample Data Structure

The agent works with comprehensive client data including:

- **Personal Information**: Name, date of birth, nationality, contact details
- **Financial Information**: Income, assets, profession, source of wealth
- **Investment Profile**: Risk profile, objectives, investment horizon
- **Portfolio Data**: Strategy, performance metrics, individual positions

## 🔒 Security Features

- **DefaultAzureCredential**: Uses Azure's recommended authentication method
- **No Hardcoded Credentials**: All sensitive data comes from environment variables
- **Input Validation**: Validates user inputs before processing
- **Error Handling**: Graceful error handling without exposing sensitive information

## 🎛️ Agent Instructions

The agent follows these strict guidelines:

1. **Required Information**: Must have either client ID or full name to proceed
2. **No Guessing**: Won't ask for missing information or make assumptions
3. **Function-Only Responses**: Uses only provided CRM functions, no general knowledge
4. **Concise Answers**: Provides specific, relevant information without unnecessary details
5. **Accurate Data**: Ensures all information comes from CRM data sources

## 🧪 Testing

Run the test suite to verify functionality:

```bash
cd agents/crm
python test_crm_functions.py
```

The tests verify:
- ✅ Successful data retrieval by client name
- ✅ Successful data retrieval by client ID  
- ✅ Proper error handling for non-existent clients
- ✅ JSON response format validation

## 🛠️ Utility Tools

### Agent Management (`list_agents.py`)

List all agents in the project:
```bash
python list_agents.py
```

Delete an agent by name:
```bash
python list_agents.py delete crm-agent
```

This utility helps manage agents in your Azure AI Foundry project, preventing duplicate agents and helping with cleanup.

> **Note**: The Foundry agent name for this CRM agent is `moneta-crm-banking-agent`.

## 💡 Agent Lifecycle Management

The CRM agent now includes intelligent lifecycle management:

### **🔍 Agent Discovery**
- Automatically checks for existing agents with the same name
- Reuses existing agents instead of creating duplicates
- Updates existing agents with latest function definitions

### **🆕 Smart Creation**
- Only creates new agents when none exist
- Preserves agent configurations across sessions
- Maintains consistent naming conventions

### **🗑️ Cleanup Options**
- **New Agents**: Prompts user whether to keep or delete
- **Existing Agents**: Preserves them by default
- **Manual Cleanup**: Use `list_agents.py` utility for batch management

## 🔄 Extending the Implementation

To extend this implementation:

1. **Add More Sample Data**: Extend `client_sample.json` with additional clients
2. **Add New Functions**: Create additional CRM functions in `crm_functions.py`
3. **Database Integration**: Replace JSON file with actual database connections
4. **Enhanced Security**: Add additional authentication and authorization layers

## 🚨 Important Notes

- The agent will **not** ask for missing client information
- All responses are based **only** on provided CRM functions
- Ensure proper Azure authentication before running
- The `--prerelease=allow` flag is required for dependency installation

## 📖 References

This implementation follows Azure AI best practices:
- Uses managed identity for secure authentication
- Implements proper error handling and logging
- Follows Azure SDK patterns and conventions
- Enables secure, scalable agent deployments
