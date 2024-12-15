# CRM Agent 
from pydantic import BaseModel, Field
import json
import os
import logging
from gbb.genai_vanilla_agents.agent import Agent
from gbb.agents.fsi_banking.config import create_llm
from typing import List, Annotated, Optional
import requests
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient


product_agent = Agent(  
    id="Funds",
    system_message="""You are an assistant that searches general information about investments funds and ETFs.

        **Your Responsibilities:**
        - **Handle all user requests that do NOT include a client's name or an id.**
        - Provide information about investments funds and ETFs by using the provided function: 'search_product'.
        - Offer clear and helpful answers to the user's inquiries. Don't use your general knowledge to respond but only the provided function.
        - If you are unsure ask the planner agent to clarify the user inquiry.
        
    """,  
    llm=create_llm(),  
    description="""Call this Agent if:
        - You need to retrieve generic funds or ETF information or conditions or other details about investments offering.
        DO NOT CALL THIS AGENT IF:  
        - You need to search for specific client's data identified by a client name or id in the request
        - You need to search for news or articles on the web
        - You need to search for in-house views or reccomandations about investement strategies""",
    )  



def search(query: str):
    service_endpoint = os.getenv('AI_SEARCH_ENDPOINT')
    index_name = os.getenv('AI_SEARCH_FUNDS_INDEX_NAME')

    search_client = SearchClient(service_endpoint, index_name, DefaultAzureCredential())
    payload = json.dumps(
        {
            "search": query,
            "vectorQueries": [
                {
                "kind": "text",
                "text": query,
                "fields": os.getenv('AI_SEARCH_VECTOR_FIELD_NAME',"contentVector")
                }
            ],
            "queryType": "semantic",
            "semanticConfiguration": os.getenv('AI_SEARCH_FUNDS_SEMANTIC_CONFIGURATION'),
            "captions": "extractive",
            "answers": "extractive|count-3",
            "queryLanguage": "en-US"
        }
    )

    response = list(search_client.search(payload))

    output = []
    for result in response:
        result.pop("parent_id")
        result.pop("chunk_id")
        result.pop("contentVector")
        output.append(result)

    return output
    
    
@product_agent.register_tool(description="Search investments funds and ETFs product details")
def search_product(query:Annotated[str,"The query to search for"]) -> str:
    """
    Search investments funds and ETFs product details by permorming a POST request to an Azure AI Search using the specified search body.

    Parameters:
    query

    Returns:
    dict: The search results in JSON format.
    """
    return search(query)