# Funds Agent - Generic Funds and ETFs Information Assistant

## Overview

The Funds Agent is an AI-powered assistant that provides comprehensive information about generic funds and ETFs by calling external data sources. This agent uses Azure AI Search to query fund databases and provide detailed insights about fund performance, holdings, sector exposures, and other relevant metrics.

## Features

- **Fund Information Access**: Query detailed information about mutual funds and ETFs
- **Holdings Analysis**: Get comprehensive data on fund top holdings and allocations
- **Performance Metrics**: Access historical performance data and risk metrics
- **Sector Exposure**: Detailed sector allocation and exposure information
- **Expense Analysis**: Information about expense ratios and fees
- **Semantic Search**: Advanced AI-powered search capabilities using Azure AI Search
- **Smart Agent Management**: Automatic agent discovery and reuse
- **Conversation History**: Complete conversation logging and management

## Architecture

### Components

1. **Funds Agent (`funds_agent.py`)**: Main agent implementation with Azure AI Foundry integration
2. **Funds Functions (`funds_functions.py`)**: AI Search functions for fund data retrieval
3. **Test Suite (`test_funds_functions.py`)**: Comprehensive testing for all functions

### Dependencies

- Azure AI Agents (>=1.1.0b4)
- Azure AI Search (>=11.4.0)
- Azure Identity for secure authentication
- Python-dotenv for environment management

## Setup Instructions

### 1. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Add the following to your root `.env` file:

```env
# Azure AI Foundry Project (shared)
PROJECT_ENDPOINT=https://your-project-name.azure.ai/
MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# Funds-specific Azure AI Search Configuration
FUNDS_AI_SEARCH_ENDPOINT=https://your-funds-search-service.search.windows.net
FUNDS_AI_SEARCH_INDEX_NAME=funds-data
FUNDS_AI_SEARCH_SEMANTIC_CONFIG_NAME=default
FUNDS_AI_SEARCH_VECTOR_FIELD_NAME=contentVector
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: This requires pre-release packages:
```bash
pip install --pre azure-ai-agents azure-ai-projects
```

### 3. Authentication Setup

The agent uses Azure Default Credential for secure authentication. Ensure you're authenticated with Azure CLI:

```bash
az login
```

### 4. Azure AI Search Setup

Ensure your Azure AI Search service has:
- A search index with funds and ETFs data
- Semantic search configuration enabled
- Vector search capabilities configured
- Proper RBAC permissions for the authenticated user

## Usage

### Running the Funds Agent

```bash
python funds_agent.py
```

### Example Queries

The agent can handle various fund-related queries:

- "Show me the top holdings of VOO ETF"
- "What is the expense ratio of Vanguard S&P 500 ETF?"
- "Compare the performance of SPY vs VOO"
- "What are the best low-cost technology ETFs?"
- "Show me the sector exposure of QQQ"
- "Find growth funds with expense ratios under 0.1%"

### Sample Interaction

```
📊 You're chatting with: funds-agent (asst_xxx)
This agent provides information about generic funds and ETFs.
Ask about fund performance, holdings, sector exposures, or ETF details.
Type 'quit' to exit.

Enter your funds/ETFs query: What are the top holdings of VOO ETF?

💰 Funds Agent Response: The Vanguard S&P 500 ETF (VOO) top holdings are:

1. Apple Inc (AAPL) - 7.15%
2. Microsoft Corp (MSFT) - 6.89%
3. Alphabet Inc Class A (GOOGL) - 2.15%
4. Amazon.com Inc (AMZN) - 2.09%
5. NVIDIA Corp (NVDA) - 2.05%

The fund has a low expense ratio of 0.03% and tracks the S&P 500 index with 
$450.2B in assets under management...
```

## Testing

Run the comprehensive test suite:

```bash
pytest test_funds_functions.py -v
```

The tests cover:
- Function initialization and configuration
- Search functionality with mocked Azure AI Search
- Error handling and exception management
- Multiple fund results handling
- Parameter validation and search configuration
- Wrapper function testing

## Security Features

- **Azure Managed Identity**: Secure authentication without hardcoded credentials
- **Least Privilege**: Minimal required permissions for search operations
- **Environment Variables**: Secure configuration management
- **Error Handling**: Comprehensive error management without exposing sensitive information

## Agent Lifecycle Management

The Funds agent includes smart lifecycle management:

1. **Discovery**: Automatically finds existing agents by name
2. **Reuse**: Uses existing agents when available
3. **Updates**: Updates existing agents with latest function configurations
4. **Cleanup**: Offers cleanup options for newly created agents

## Function Schema

The agent exposes one main function:

### `search_funds_details(query: str) -> str`

**Description**: Search for generic funds and ETFs information including holdings, performances, sector exposures

**Parameters**:
- `query` (string): The search query for funds, ETFs, holdings, performance, or sector information

**Returns**: JSON string containing search results with funds and ETFs details

**Key Features**:
- Includes ALL relevant details (holdings, sector exposures, performances)
- Passes user question AS IS to maintain query intent
- Provides comprehensive fund information

## Error Handling

The agent includes comprehensive error handling:

- **Search Service Errors**: Graceful handling of Azure AI Search service issues
- **Authentication Errors**: Clear feedback on authentication problems
- **Configuration Errors**: Validation of required environment variables
- **Network Errors**: Retry logic and timeout handling

## Integration

### With Azure AI Foundry

The agent integrates seamlessly with Azure AI Foundry:
- Uses FunctionTool for search capabilities
- Supports automatic function calling
- Provides conversation threading and history
- Includes proper agent lifecycle management

### With Azure AI Search

The agent leverages Azure AI Search capabilities:
- Semantic search for better relevance
- Vector search for similarity matching
- Extractive answers for precise responses
- Configurable result count and ranking

## Data Types Supported

The agent can provide information about:

### ETFs (Exchange-Traded Funds)
- Ticker symbols and fund names
- Expense ratios and AUM
- Top holdings and weightings
- Sector allocations
- Performance metrics
- Risk indicators (beta, standard deviation, Sharpe ratio)

### Mutual Funds
- Fund names and tickers
- Minimum investment requirements
- Share classes and expense ratios
- Holdings and sector exposure
- Historical performance
- Risk metrics

### Performance Metrics
- 1, 3, 5, and 10-year returns
- Risk-adjusted returns
- Benchmark comparisons
- Volatility measures

### Holdings Analysis
- Top 5-10 holdings
- Sector weightings
- Geographic allocations
- Asset class distributions

## Monitoring and Logging

The agent includes comprehensive logging:
- Search query logging
- Performance metrics
- Error tracking
- Conversation history

## Best Practices

1. **Query Specificity**: Use specific fund names or tickers for better results
2. **Comprehensive Queries**: Ask for specific details (holdings, performance, expenses)
3. **Source Verification**: Always verify fund information from official sources
4. **Regular Updates**: Keep the search index updated with latest fund data
5. **Security**: Regularly review and update authentication credentials

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure Azure CLI is logged in and has proper permissions
2. **Search Service Unavailable**: Verify Azure AI Search service is running and accessible
3. **No Results**: Check search index configuration and fund data availability
4. **Function Errors**: Verify environment variables are properly configured

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ENDPOINT` | Azure AI Foundry project endpoint | `https://your-project.azure.ai/` |
| `MODEL_DEPLOYMENT_NAME` | Model deployment name | `gpt-4o-mini` |
| `FUNDS_AI_SEARCH_ENDPOINT` | Funds search service endpoint | `https://your-search.search.windows.net` |
| `FUNDS_AI_SEARCH_INDEX_NAME` | Search index name | `funds-data` |
| `FUNDS_AI_SEARCH_SEMANTIC_CONFIG_NAME` | Semantic configuration | `default` |
| `FUNDS_AI_SEARCH_VECTOR_FIELD_NAME` | Vector field name | `contentVector` |

## Contributing

When contributing to the Funds agent:

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new functionality
3. Update documentation for any changes
4. Ensure security best practices are maintained
5. Test with various fund types and query scenarios

## License

This project is part of the Microsoft Learn AI Agents training materials.
