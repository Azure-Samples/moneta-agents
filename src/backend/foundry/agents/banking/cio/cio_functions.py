"""
CIO (Chief Investment Office) functions for accessing investment research and in-house views.
This module provides AI Search capabilities for querying investment research documents.
"""

import os
import json
import logging
from typing import Annotated
from pathlib import Path
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery
from azure.identity import DefaultAzureCredential

# Import tracing utilities from backend root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from tracing import get_tracing_manager


class CIOSearchFunctions:
    """
    CIO Search Functions for accessing investment research and in-house views from Moneta Bank.
    Uses Azure AI Search for semantic search capabilities.
    """
    
    def __init__(self):
        """Initialize the CIO Search Functions with Azure AI Search client."""
        self.search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
        self.search_index_name = os.getenv("AI_SEARCH_CIO_INDEX_NAME")
        self.semantic_configuration_name = os.getenv("AI_SEARCH_CIO_SEMANTIC_CONFIGURATION", "default")
        
        if not self.search_endpoint or not self.search_index_name:
            raise ValueError("AI_SEARCH_ENDPOINT and AI_SEARCH_CIO_INDEX_NAME environment variables are required")
        
        # Initialize Azure AI Search client with managed identity
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.search_index_name,
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            )
        )
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def search_cio(self, query: Annotated[str, "The query to search for investment research and CIO views"]) -> Annotated[str, "The search results in JSON format"]:
        """
        Search for investment research and CIO views from Moneta Bank documents.
        
        Args:
            query: The search query for investment research, market analysis, or CIO recommendations
            
        Returns:
            JSON string containing search results with investment research and recommendations
        """
        tracing_manager = get_tracing_manager()
        
        try:
            with tracing_manager.trace_function_call(
                "search_cio",
                parameters={
                    "query": query,
                    "search_endpoint": self.search_endpoint,
                    "index_name": self.search_index_name
                }
            ):
                # Create vector query for semantic search
                text_vector_query = VectorizableTextQuery(
                    kind="text",
                    text=query,
                    fields=os.getenv('CIO_AI_SEARCH_VECTOR_FIELD_NAME', "contentVector")
                )

                # Perform semantic search with vector queries
                results = self.search_client.search(
                    search_text=query,
                    include_total_count=True,
                    vector_queries=[text_vector_query],
                    query_type="semantic",
                    semantic_configuration_name=self.semantic_configuration_name,
                    query_answer="extractive",
                    top=3,
                    query_answer_count=3
                )

                # Process search results
                response = list(results)
                output = []
                
                for result in response:
                    # Remove internal fields from response
                    result.pop("parent_id", None)
                    result.pop("chunk_id", None)
                    result.pop(os.getenv('CIO_AI_SEARCH_VECTOR_FIELD_NAME', "contentVector"), None)
                    output.append(result)

                self.logger.info(f"CIO search completed for query: '{query}' - Found {len(output)} results")
                return json.dumps(output, indent=2)
            
        except Exception as e:
            # Log error in trace if available
            if tracing_manager and tracing_manager.is_configured:
                with tracing_manager.trace_function_call(
                    "search_cio_error",
                    parameters={"error": str(e), "query": query}
                ):
                    pass
                    
            self.logger.error(f"An unexpected error occurred in the 'search_cio' function: {e}")
            return json.dumps({
                "error": f"Search failed: {str(e)}",
                "query": query,
                "results": []
            })


# Global instance will be initialized when first used
_cio_search_functions = None

def get_cio_search_functions():
    """Get or create the global CIO search functions instance."""
    global _cio_search_functions
    if _cio_search_functions is None:
        _cio_search_functions = CIOSearchFunctions()
    return _cio_search_functions

# Function mapping for agent execution
def search_cio(query: str) -> str:
    """Wrapper function for agent execution."""
    return get_cio_search_functions().search_cio(query)

# Export functions for agent registration
cio_functions = [search_cio]
