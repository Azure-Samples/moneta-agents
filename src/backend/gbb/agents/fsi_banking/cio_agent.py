# CRM Agent 
import json
import os
import logging
from gbb.genai_vanilla_agents.agent import Agent
from gbb.agents.fsi_banking.config import create_llm   
from typing import List, Annotated, Optional
import requests
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient


cio_agent = Agent(  
    id="CIO",
    system_message="""You are an assistant that retrieve investement researches from documents produced by the CIO (Chief Investment Office) and in-house view from Moneta Bank.
        
        **Your Responsibilities:**
        - Provide information about researches from documents produced by the CIO (Chief Investment Office) and in-house view from Moneta Bank by using the provided function: 'search_cio'.
        - Offer clear and helpful answers to the user's inquiries. Don't use your general knowledge to respond but only the provided function.
        - If you are unsure ask the planner agent to clarify the user inquiry.
        - 
    
    """,  
    llm=create_llm(),
    description="""Call this Agent if:
        - You need to retrieve investement researches or in-house views or reccomandations about investing streategies.
        DO NOT CALL THIS AGENT IF:  
        - You need to search for specific client's data identified by a client name or id in the request
        - You need to fetch generic investments answers about stock funds or etf
        - You need to search for news or articles on the web""",
)  



def search(query: str):
    service_endpoint = os.getenv('AI_SEARCH_ENDPOINT')
    index_name = os.getenv('AI_SEARCH_CIO_INDEX_NAME')

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
            "semanticConfiguration": "default",
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

    logging.info(f"CIO Agent RAG Query= {query}")
    logging.info(f"CIO Agent RAG results= {output}")
    return output
    
    
@cio_agent.register_tool(description="Search investement overview, in-house investment view and reccomendations from Moneta Bank and CIO.")
def search_cio(query:Annotated[str,"The query to search for"]) -> str:
    """
    Search and retrieve investement research and in-house views from Moneta Bank by permorming a POST request to an Azure AI Search using the specified search body.

    Parameters:
    query

    Returns:
    dict: The search results in JSON format.
    """
    return search(query)