# CIO Agent - Chief Investment Office Research Assistant

## Overview

The CIO (Chief Investment Office) Agent is an AI-powered assistant that provides access to investment research, market analysis, and in-house views from Moneta Bank's Chief Investment Office. This agent uses Azure AI Search to query investment documents and provide relevant insights.

## Features

- **Investment Research Access**: Query investment research documents from the CIO
- **Market Analysis**: Get insights on market trends and analysis
- **In-House Views**: Access Moneta Bank's strategic investment perspectives
- **Semantic Search**: Advanced AI-powered search capabilities using Azure AI Search
- **Smart Agent Management**: Automatic agent discovery and reuse
- **Conversation History**: Complete conversation logging and management

## Architecture

### Components

1. **CIO Agent (`cio_agent.py`)**: Main agent implementation with Azure AI Foundry integration
2. **CIO Functions (`cio_functions.py`)**: AI Search functions for document retrieval
3. **Test Suite (`test_cio_functions.py`)**: Comprehensive testing for all functions

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

Required environment variables:

```env
# Azure AI Foundry Project
PROJECT_ENDPOINT=https://your-project-name.azure.ai/
MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# Azure AI Search Configuration
AI_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AI_SEARCH_INDEX_NAME=cio-documents
AI_SEARCH_SEMANTIC_CONFIG_NAME=default
AI_SEARCH_VECTOR_FIELD_NAME=contentVector
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
- A search index with investment documents
- Semantic search configuration enabled
- Vector search capabilities configured
- Proper RBAC permissions for the authenticated user

## Usage

### Running the CIO Agent

```bash
python cio_agent.py
```

### Example Queries

The agent can handle various investment-related queries:

- "What are the latest investment recommendations for Q4 2024?"
- "Show me the market outlook for technology stocks"
- "What is the CIO's view on emerging markets?"
- "Find research on ESG investment strategies"
- "What are the current interest rate predictions?"

### Sample Interaction

```
📈 You're chatting with: cio-agent (asst_xxx)
This agent provides investment research and CIO views from Moneta Bank documents.
Ask about market analysis, investment recommendations, or strategic views.
Type 'quit' to exit.

Enter your investment research query: What are the latest recommendations for tech stocks?

📊 CIO Agent Response: Based on our latest research, the CIO recommends maintaining 
an overweight position in technology stocks for Q4 2024. Key recommendations include:

1. Focus on AI and cloud infrastructure companies
2. Selective exposure to semiconductor stocks
3. Caution on high-growth, high-valuation names

The research indicates strong fundamentals in enterprise software and 
cybersecurity sectors...
```

## Testing

Run the comprehensive test suite:

```bash
pytest test_cio_functions.py -v
```

The tests cover:
- Function initialization and configuration
- Search functionality with mocked Azure AI Search
- Error handling and exception management
- Schema validation for agent integration
- Parameter validation and search configuration

## Security Features

- **Azure Managed Identity**: Secure authentication without hardcoded credentials
- **Least Privilege**: Minimal required permissions for search operations
- **Environment Variables**: Secure configuration management
- **Error Handling**: Comprehensive error management without exposing sensitive information

## Agent Lifecycle Management

The CIO agent includes smart lifecycle management:

1. **Discovery**: Automatically finds existing agents by name
2. **Reuse**: Uses existing agents when available
3. **Updates**: Updates existing agents with latest function configurations
4. **Cleanup**: Offers cleanup options for newly created agents

## Function Schema

The agent exposes one main function:

### `search_cio(query: str) -> str`

**Description**: Search for investment research and CIO views from Moneta Bank documents

**Parameters**:
- `query` (string): The search query for investment research, market analysis, or CIO recommendations

**Returns**: JSON string containing search results with investment research and recommendations

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

## Monitoring and Logging

The agent includes comprehensive logging:
- Search query logging
- Performance metrics
- Error tracking
- Conversation history

## Best Practices

1. **Query Optimization**: Use specific, focused queries for better results
2. **Result Validation**: Always verify search results before providing recommendations
3. **Source Citation**: Reference source documents when providing investment advice
4. **Regular Updates**: Keep the search index updated with latest CIO documents
5. **Security**: Regularly review and update authentication credentials

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure Azure CLI is logged in and has proper permissions
2. **Search Service Unavailable**: Verify Azure AI Search service is running and accessible
3. **No Results**: Check search index configuration and document availability
4. **Function Errors**: Verify environment variables are properly configured

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When contributing to the CIO agent:

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new functionality
3. Update documentation for any changes
4. Ensure security best practices are maintained
5. Test with various query types and scenarios

## License

This project is part of the Microsoft Learn AI Agents training materials.
