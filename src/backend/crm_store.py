from azure.cosmos import CosmosClient, PartitionKey, exceptions
from genai_vanilla_agents.conversation import Conversation
import os
import json
import datetime
import random

class CRMStore:
    def __init__(self, url, key, database_name, container_name):
        self.client = CosmosClient(url, credential=key)
        self.database_name = database_name
        self.container_name = container_name
        self.db = None
        self.container = None
        self.initialize_database()
        self.initialize_container()

    def initialize_database(self):
        try:
            self.db = self.client.create_database_if_not_exists(id=self.database_name)
        except exceptions.CosmosResourceExistsError:
            self.db = self.client.get_database_client(database=self.database_name)

    def initialize_container(self):
        try:
            self.container = self.db.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/client_id"),
                offer_throughput=400
            )
        except exceptions.CosmosResourceExistsError:
            self.container = self.db.get_container_client(container=self.container_name)
            
        
    def create_customer_profile(self, customer_profile):
        """
        Saves the customer profile to Cosmos DB.
        
        Args:
        - customer_profile (dict): The customer profile to save.
        """
        
        try:
            # Create a new document in the container
            created_user = self.container.create_item(body=customer_profile)
            return 
        except Exception as e:
            print(f"An error occurred: {e}")
            return None


    def get_customer_profile_by_full_name(self, full_name):
        """
        Retrieves a customer profile from Cosmos DB based on a partial match of the customer's full name.
        
        Args:
        - full_name (str): The partial or full name of the customer to search for.
        
        Returns:
        - dict: The customer profile, if found.
        """
        query = "SELECT * FROM c WHERE c.fullName LIKE @full_name"
        parameters = [
            {"name": "@full_name", "value": f"%{full_name}%"}
        ]
        items = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        return items[0] if items else None
    

    def get_customer_profile_by_client_id(self, client_id):
        """
        Retrieves a customer profile from Cosmos DB based on a client_id.
        
        Args:
        - client_id (str): The client id of the customer to search for.
        
        Returns:
        - dict: The customer profile, if found.
        """
        query = "SELECT * FROM c WHERE c.clientID = @client_id"
        parameters = [
            {"name": "@client_id", "value": client_id}
        ]
        items = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        return items[0] if items else None
