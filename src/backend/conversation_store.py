from azure.cosmos import CosmosClient, PartitionKey, exceptions
import datetime
import random

class ConversationStore:
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
                partition_key=PartitionKey(path="/user_id"),
                offer_throughput=400
            )
        except exceptions.CosmosResourceExistsError:
            self.container = self.db.get_container_client(container=self.container_name)
            
        
        # User (RM)
    def create_user(self, user_id, user_data):
        # Ensure the user_data dict has an 'id' key
        user_data['id'] = user_id  # Use the user_id as the document 'id'
        
        try:
            # Create a new document in the container
            created_user = self.container.create_item(body=user_data)
            print(f"Created new user with id: {user_id}")
            return 
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def read_user_info(self, user_id):
        query = "SELECT * FROM c WHERE c.id=@userId"
        parameters = [{"name": "@userId", "value": user_id}]
        items = list(self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        if items:
            item_dict = items[0]
            # values_dict = {key : value for key, value in item_dict.items() if not key.startswith('_')}
            return item_dict
        else:
            return None

    def update_user_info(self, user_id, updated_info):
        # Read the current information to get the document's id and _etag
        user_document = self.read_user_info(user_id)
        if not user_document:
            return None  # User does not exist

        # Update the document with new information
        for key, value in updated_info.items():
            user_document[key] = value
        
        # Replace the document in the database
        updated_document = self.container.replace_item(
            item=user_document,
            body=user_document
        )
        return updated_document
    
    
    def generate_chat_id(self):
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        random_digits = "{:03d}".format(random.randint(0, 999))
        chat_id = f"{date_str}_{random_digits}"
        return chat_id
    
    def list_user_chats(self, user_id):
        user_data = self.read_user_info(user_id)
        chat_histories = user_data.get('chat_histories', {})
        return list(chat_histories.keys())
    
    def wipe_user_chats(self, user_id):
        user_data = self.read_user_info(user_id)
        user_data['chat_histories'] = {}
        self.update_user_info(user_id, user_data)