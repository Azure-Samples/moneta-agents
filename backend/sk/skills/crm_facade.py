import json
import os
import logging

from typing import Annotated
from semantic_kernel.functions import kernel_function

from crm_store import CRMStore

class CRMFacade:
    """ 
    The class acts as an facade for the crm_store.
    The facade is only required if the same CRM Store to be used by both Vanilla and SK frameworks
    Once a single framwork is adopted it can be retired.
    """
    
    def __init__(self, key, cosmosdb_endpoint, crm_database_name, crm_container_name):
        self.crm_db = CRMStore(
            url=cosmosdb_endpoint,
            key=key,
            database_name=crm_database_name,
            container_name=crm_container_name)

    @kernel_function(
        name="load_from_crm_by_client_fullname",
        description="Load insured client data from the CRM from the given full name")
    def get_customer_profile_by_full_name(self,
                                          full_name: Annotated[str,"The customer full name to search for"]) -> Annotated[str, "The output is a customer profile"]:
        response = self.crm_db.get_customer_profile_by_full_name(full_name)
        return json.dumps(response) if response else None

    @kernel_function(
        name="load_from_crm_by_client_id",
        description="Load insured client data from the CRM from the client_id")
    def get_customer_profile_by_client_id(self, 
                                          client_id: Annotated[str,"The customer client_id to search for"]) -> Annotated[str, "The output is a customer profile"]:
        response = self.crm_db.get_customer_profile_by_client_id(client_id)
        return json.dumps(response) if response else None
        
