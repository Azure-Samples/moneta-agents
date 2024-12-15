# CRM Agent 
from pydantic import BaseModel, Field
import json
import os
import logging
from gbb.genai_vanilla_agents.agent import Agent
from gbb.agents.fsi_insurance.config import llm
from typing import List, Annotated, Optional
from crm_store import CRMStore
from azure.identity import DefaultAzureCredential

crm_agent = Agent(  
    id="CRM",
    system_message="""You are an assistant that interacts with CRM data.
        
        **Your Responsibilities:**
        - **Only respond to user requests that explicitly mention the names of a client or the client id.**
        - When the user's request includes the name of a client or the client id then retrieve information about the client and their policies, coverages, premiums by using one of the provided functions.
        - Provide concise and accurate information based only on the CRM data. Don't come up with information that are not coming form the CRM.
    
    """,  
    llm=create_llm(),  
    description="""Call this Agent if:
        - You need to retrieve specific client's data identified by the name of a client in the user request or by a client id.
        DO NOT CALL THIS AGENT IF:  
        - You need to fetch generic investments answers about stock funds or etf
        - You need to search for news or articles on the web
        - You need to search for in-house views or reccomandations about investement strategies""", 
)  

key = DefaultAzureCredential()
db = CRMStore(
        url=os.getenv("COSMOSDB_ENDPOINT"),
        key=key,
        database_name=os.getenv("COSMOSDB_DATABASE_NAME"),
        container_name=os.getenv("COSMOSDB_CONTAINER_CLIENT_NAME")
    )

@crm_agent.register_tool(description="Load insured client data from the CRM from the given full name")
def load_from_crm_by_client_fullname(full_name:Annotated[str,"The customer full name to search for"]) -> str:
    """
    Load an insured client data and policies into a pandas DataFrame.

    Parameters:
    full_name (str): full_name of the client to search for

    Returns:
    pd.DataFrame: DataFrame containing the loaded data
    """
    try:
        return db.get_customer_profile_by_full_name(full_name)
           
    except Exception as e:
        print(f"An unexpected error occurred loading client data from the DB: {e}") 

@crm_agent.register_tool(description="Load insured client data from the CRM by client_id")
def load_from_crm_by_client_id(client_id:Annotated[str,"The customer client_id to search for"]) -> str:
    """
    Load insured client data from the CRM by client_id into a pandas DataFrame.

    Parameters:
    client_id (str): the client_id of the client to search for

    Returns:
    pd.DataFrame: DataFrame containing the loaded data
    """
    try:
        return db.get_customer_profile_by_client_id(client_id)
           
    except Exception as e:
        print(f"An unexpected error occurred loading client data from the DB: {e}") 