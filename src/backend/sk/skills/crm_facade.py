import json
from typing import Any, Callable, Set, Dict, List, Optional
from crm_store import CRMStore
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

COSMOSDB_ENDPOINT=os.environ["COSMOSDB_ENDPOINT"]
COSMOSDB_DATABASE_NAME=os.environ["COSMOSDB_DATABASE_NAME"]
COSMOSDB_CONTAINER_CLIENT_NAME=os.environ["COSMOSDB_CONTAINER_CLIENT_NAME"]

crm_db = CRMStore(
        url=COSMOSDB_ENDPOINT,
        key=DefaultAzureCredential(),
        database_name=COSMOSDB_DATABASE_NAME,
        container_name=COSMOSDB_CONTAINER_CLIENT_NAME)

# These are the user-defined functions that can be called by the agent.
def load_from_crm_by_client_fullname(full_name: str) -> str:
    """
    Load insured client data from the CRM from the given full name.
    
    :param fullname: The customer full name to search for.
    :return: The output is a customer profile.
    """

    response = crm_db.get_customer_profile_by_full_name(full_name)
    return json.dumps(response) if response else None

def load_from_crm_by_client_id(client_id: str) -> str:
    """
    Load insured client data from the CRM from the client_id.
    
    :param client_id: The customer client_id to search for.
    :return: The output is a customer profile.
    """

    response = crm_db.get_customer_profile_by_client_id(client_id)
    return json.dumps(response) if response else None

#Statically defined user functions for fast reference
crm_functions: Set[Callable[..., Any]] = {
    load_from_crm_by_client_fullname,
    load_from_crm_by_client_id,
}