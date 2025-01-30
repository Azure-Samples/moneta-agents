import json
import os
import logging
import requests
import pandas as pd
from requests_html import HTMLSession
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from crm_store import CRMStore

# If you still rely on a CRMStore class (from 'crm_store.py'), make sure it's imported:
# from crm_store import CRMStore

###############################################################################
# CIO-Related Search (Previously CIOFacade)
###############################################################################
def search_cio(query: str) -> str:
    """
    Search details about investments, recommendations, or in-house CIO (Chief Investment Office) views.
    
    This function replaces the Semantic Kernel-based search() method in the previous CIOFacade class.
    It uses Azure Cognitive Search with a vector query to retrieve the top 3 most relevant results.
    """


    try:
        service_endpoint = os.getenv("AI_SEARCH_ENDPOINT") or ""
        index_name = os.getenv("AI_SEARCH_CIO_INDEX_NAME") or ""
        semantic_configuration_name = os.getenv("AI_SEARCH_CIO_SEMANTIC_CONFIGURATION") or ""
        search_key = os.getenv("AI_SEARCH_KEY") or ""

        # Use AzureKeyCredential if you want to pass key directly, or if you have
        # a credential object from managed identity, pass that instead.
        credential = AzureKeyCredential(search_key)
        search_client = SearchClient(service_endpoint, index_name, credential)

        # Prepare vector query
        text_vector_query = VectorizableTextQuery(
            kind="text",
            text=query,
            fields=os.getenv('AI_SEARCH_VECTOR_FIELD_NAME', "text-vector")
        )

        # Execute semantic (vector) search
        results = search_client.search(
            search_text=query,
            include_total_count=True,
            vector_queries=[text_vector_query],
            query_type="semantic",
            semantic_configuration_name=semantic_configuration_name,
            query_answer="extractive",
            top=3,
            query_answer_count=3
        )

        # Convert the response to a Python list and remove vector-based fields
        response_list = list(results)
        output = []
        for result in response_list:
            # Remove fields not needed in the output
            result.pop("parent_id", None)
            result.pop("chunk_id", None)
            result.pop(os.getenv('AI_SEARCH_VECTOR_FIELD_NAME', "text-vector"), None)
            output.append(result)

        return json.dumps(output)
    except Exception as e:
        logging.error(f"Error in search_cio: {str(e)}")
        return json.dumps({"error": f"search_cio failed with error: {str(e)}"})


###############################################################################
# CRM Lookups (Previously CRMFacade)
###############################################################################
def load_from_crm_by_client_fullname(full_name: str) -> str:
    """
    Load insured client data from the CRM using the given full name.
    
    This function replaces the SK-based get_customer_profile_by_full_name 
    from the CRMFacade class.
    """
    try:
        # Example of how to pull from environment variables:
        cosmosdb_endpoint = os.getenv("COSMOSDB_ENDPOINT") or ""
        crm_database_name = os.getenv("COSMOSDB_DATABASE_NAME") or ""
        crm_container_name = os.getenv("COSMOSDB_CONTAINER_CLIENT_NAME") or ""
        key=DefaultAzureCredential()
        
        crm_db = CRMStore(
             url=cosmosdb_endpoint,
             key=key,
             database_name=crm_database_name,
             container_name=crm_container_name
        )

        response = crm_db.get_customer_profile_by_full_name(full_name)
        return json.dumps(response) if response else None

    except Exception as e:
        logging.error(f"Error in load_from_crm_by_client_fullname: {str(e)}")
        return json.dumps({"error": f"load_from_crm_by_client_fullname failed with error: {str(e)}"})


def load_from_crm_by_client_id(client_id: str) -> str:
    """
    Load insured client data from the CRM using the client_id.
    
    This function replaces the SK-based get_customer_profile_by_client_id 
    from the CRMFacade class.
    """
    try:

        cosmosdb_endpoint = os.getenv("COSMOSDB_ENDPOINT") or ""
        crm_database_name = os.getenv("COSMOSDB_DATABASE_NAME") or ""
        crm_container_name = os.getenv("COSMOSDB_CONTAINER_CLIENT_NAME") or ""
        key=DefaultAzureCredential()
        
        crm_db = CRMStore(
            url=cosmosdb_endpoint,
            key=key,
            database_name=crm_database_name,
            container_name=crm_container_name
        )
        
        response = crm_db.get_customer_profile_by_client_id(client_id)
        return json.dumps(response) if response else None

    except Exception as e:
        logging.error(f"Error in load_from_crm_by_client_id: {str(e)}")
        return json.dumps({"error": f"load_from_crm_by_client_id failed with error: {str(e)}"})


###############################################################################
# Funds Search (Previously FundsFacade)
###############################################################################
def search_funds_details(query: str) -> str:
    """
    Search details about Funds or ETFs.
    
    This function replaces the Semantic Kernel-based search() method 
    in the previous FundsFacade class.
    """
    try:
        service_endpoint = os.getenv("AI_SEARCH_ENDPOINT") or ""
        index_name = os.getenv("AI_SEARCH_FUNDS_INDEX_NAME") or ""
        semantic_configuration_name = os.getenv("AI_SEARCH_FUNDS_SEMANTIC_CONFIGURATION") or ""
        search_key = os.getenv("AI_SEARCH_KEY") or ""

        credential = AzureKeyCredential(search_key)
        search_client = SearchClient(service_endpoint, index_name, credential)

        text_vector_query = VectorizableTextQuery(
            kind="text",
            text=query,
            fields=os.getenv('AI_SEARCH_VECTOR_FIELD_NAME', "text-vector")
        )

        results = search_client.search(
            search_text=query,
            include_total_count=True,
            vector_queries=[text_vector_query],
            query_type="semantic",
            semantic_configuration_name=semantic_configuration_name,
            query_answer="extractive",
            top=3,
            query_answer_count=3
        )

        response_list = list(results)
        output = []
        for result in response_list:
            # Remove fields not needed in the output
            result.pop("parent_id", None)
            result.pop("chunk_id", None)
            result.pop(os.getenv('AI_SEARCH_VECTOR_FIELD_NAME', "text-vector"), None)
            output.append(result)

        return json.dumps(output)
    except Exception as e:
        logging.error(f"Error in search_funds_details: {str(e)}")
        return json.dumps({"error": f"search_funds_details failed with error: {str(e)}"})


###############################################################################
# News Retrieval (Previously NewsFacade)
###############################################################################
def search_news(position: str) -> str:
    """
    Search for investment news and articles from the web for a specific position (ticker).
    
    This function replaces the SK-based fetch_news() method in the previous NewsFacade class.
    It uses Finviz scraping as a demonstration. In production, you might replace
    this with a proper news API or curated feed.
    
    NOTE: If requests_html + Finviz scraping is not permissible in production,
    consider using an official news API.
    """
    try:
        url = f'https://finviz.com/quote.ashx?t={position}'
        session = HTMLSession()
        response = session.get(url)

        if not response or response.status_code != 200:
            return json.dumps({"error": f"Unable to fetch news for {position} (status code {response.status_code if response else 'N/A'})"})

        news_table = response.html.find('table.fullview-news-outer', first=True)
        if not news_table:
            return json.dumps({"message": f"No news entries found for {position}."})

        news_rows = news_table.find('tr')
        logging.info(f"Found {len(news_rows)} news entries for {position}.")

        news_list = []
        last_date = None
        # Extract data for the first 5 news entries
        for row in news_rows[:5]:
            # Date and time parsing
            date_data = row.find('td', first=True).text.strip()
            date_parts = date_data.split()

            if len(date_parts) == 2:
                # Both date and time
                news_date, news_time = date_parts
                last_date = news_date
            else:
                # Only time provided
                news_date = last_date
                news_time = date_parts[0] if date_parts else ""

            # Extract headline and link
            headline_tag = row.find('a', first=True)
            news_headline = headline_tag.text if headline_tag else "N/A"
            news_link = headline_tag.attrs['href'] if headline_tag else "#"

            news_list.append({
                'Ticker': position,
                'Date': news_date,
                'Time': news_time,
                'Headline': news_headline,
                'Link': news_link
            })

        # Convert to JSON
        return json.dumps(news_list)
    except Exception as e:
        logging.error(f"An unexpected error occurred in 'search_news': {e}")
        return json.dumps({"error": f"search_news failed with error: {str(e)}"})



###############################################################################
# OpenAI Function Definitions
# These can be included in your 'TOOLS' or 'FUNCTIONS' list for function calling.
###############################################################################
def get_TOOLS():
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "search_cio",
                "description": "Search details about CIO investments, recommendations, or in-house views.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for in the CIO system"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "load_from_crm_by_client_fullname",
                "description": "Load insured client data from the CRM by client full name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "full_name": {
                            "type": "string",
                            "description": "The client's full name to search for"
                        }
                    },
                    "required": ["full_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "load_from_crm_by_client_id",
                "description": "Load insured client data from the CRM by client ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {
                            "type": "string",
                            "description": "The client's ID to search for"
                        }
                    },
                    "required": ["client_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_funds_details",
                "description": "Search details about Funds or ETFs",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for in the funds database"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_news",
                "description": "Search for investment news related to a given ticker (position)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "position": {
                            "type": "string",
                            "description": "The stock ticker or position to search for news about"
                        }
                    },
                    "required": ["position"]
                }
            }
        }
    ]

    # You can import these functions + their definitions into your existing toolchain
    # or add them to your "TOOLS" list directly, like so:
    # 
    # TOOLS = [
    #     *OPENAI_FUNCTION_DEFINITIONS,
    #     ... (other function definitions) ...
    # ]
    #
    return TOOLS


def get_FUNCTION_MAPPING():
    # Function mapping
    FUNCTION_MAPPING = {
        'load_from_crm_by_client_fullname' : load_from_crm_by_client_fullname, 
        'load_from_crm_by_client_id' : load_from_crm_by_client_id,
        'search_cio' : search_cio,
        'search_funds_details' : search_funds_details,
        'search_news' : search_news
    }
    return FUNCTION_MAPPING
