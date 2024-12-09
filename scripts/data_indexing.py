import os
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient, BlobClient
from dotenv import load_dotenv

from azure.search.documents.indexes.models import (
    SplitSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    AzureOpenAIEmbeddingSkill,
    SearchIndexerSkillset
)

from azure.search.documents.indexes import SearchIndexerClient, SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SearchIndex,
    SearchIndexer,
    FieldMapping,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    NativeBlobSoftDeleteDeletionDetectionPolicy,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    IndexProjectionMode
)

load_dotenv(override=True)  # Take environment variables from .env

# Variables
endpoint = os.environ["AI_SEARCH_ENDPOINT"]
credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY")) if os.getenv("AZURE_SEARCH_KEY") else DefaultAzureCredential()

blob_connection_string = os.environ["BLOB_CONNECTION_STRING"]
account_url = os.getenv("BLOB_ACCOUNT_URL")
account_key = AzureKeyCredential(os.getenv("BLOB_ACCOUNT_KEY")) if os.getenv("BLOB_ACCOUNT_KEY") else DefaultAzureCredential()
azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
azure_openai_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
azure_openai_model_name = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large")
azure_openai_model_dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", 1536))
chuncksize = int(os.getenv("CHUNCK_SIZE", 2000))

# Create the BlobServiceClient object
blob_service_client = BlobServiceClient(account_url, credential=account_key)

def list_container_names():
    container_names = []
    containers = blob_service_client.list_containers()
    for container in containers:
        container_names.append(container.name)
    return container_names

# Get the list of container names
container_names = list_container_names()

# Initialize clients
indexer_client = SearchIndexerClient(endpoint=endpoint, credential=credential)
index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

# Loop over each container name
for container_name in container_names:
    # Create a data source connection
    container = SearchIndexerDataContainer(name=container_name)
    data_source_connection = SearchIndexerDataSourceConnection(
        name=f"{container_name}-connection",
        type="azureblob",
        connection_string=blob_connection_string,
        container=container,
        data_deletion_detection_policy=NativeBlobSoftDeleteDeletionDetectionPolicy()
    )
    data_source = indexer_client.create_or_update_data_source_connection(data_source_connection)
    print(f"Data source '{data_source.name}' created or updated")

    # Define the search index name
    index_name = container_name

    # Define the fields for the search index
    fields = [
        SearchField(name="parent_id", type=SearchFieldDataType.String),
        SearchField(name="title", type=SearchFieldDataType.String),
        SearchField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            key=True,
            sortable=True,
            filterable=True,
            facetable=True,
            analyzer_name="keyword"
        ),
        SearchField(
            name="chunk",
            type=SearchFieldDataType.String,
            sortable=False,
            filterable=False,
            facetable=False
        ),
        SearchField(
            name="text_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=azure_openai_model_dimensions,
            vector_search_profile_name="myHnswProfile"
        )
    ]

    # Configure the vector search configuration
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="myHnsw"),
        ],
        profiles=[
            VectorSearchProfile(
                name="myHnswProfile",
                algorithm_configuration_name="myHnsw",
                vectorizer_name="myOpenAI",
            )
        ],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="myOpenAI",
                kind="azureOpenAI",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=azure_openai_endpoint,
                    deployment_name=azure_openai_embedding_deployment,
                    model_name=azure_openai_model_name
                ),
            ),
        ],
    )

    # Create the search index
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    result = index_client.create_or_update_index(index)
    print(f"Search index '{result.name}' created")

    # Define index projections inside the loop
    index_projections = SearchIndexerIndexProjection(
        selectors=[
            SearchIndexerIndexProjectionSelector(
                target_index_name=index_name,
                parent_key_field_name="parent_id",
                source_context="/document/pages/*",
                mappings=[
                    InputFieldMappingEntry(name="chunk", source="/document/pages/*"),
                    InputFieldMappingEntry(name="text_vector", source="/document/pages/*/text_vector"),
                    InputFieldMappingEntry(name="title", source="/document/metadata_storage_name"),
                ],
            ),
        ],
        parameters=SearchIndexerIndexProjectionsParameters(
            projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
        ),
    )

    # Create a skillset  
    skillset_name = f"{container_name}-skillset"

    split_skill = SplitSkill(  
        description="Split skill to chunk documents",  
        text_split_mode="pages",  
        context="/document",  
        maximum_page_length=chuncksize,  
        page_overlap_length=500,  
        inputs=[  
            InputFieldMappingEntry(name="text", source="/document/content"),  
        ],  
        outputs=[  
            OutputFieldMappingEntry(name="textItems", target_name="pages")  
        ],  
    )  
    
    embedding_skill = AzureOpenAIEmbeddingSkill(  
        description="Skill to generate embeddings via Azure OpenAI",  
        context="/document/pages/*",  
        resource_url=azure_openai_endpoint,  
        deployment_name=azure_openai_embedding_deployment,	  
        model_name=azure_openai_model_name,
        dimensions=azure_openai_model_dimensions,
        inputs=[  
            InputFieldMappingEntry(name="text", source="/document/pages/*"),  
        ],  
        outputs=[  
            OutputFieldMappingEntry(name="embedding", target_name="text_vector")  
        ],  
    )
    
    index_projections = SearchIndexerIndexProjection(  
        selectors=[  
            SearchIndexerIndexProjectionSelector(  
                target_index_name=index_name,  
                parent_key_field_name="parent_id",  
                source_context="/document/pages/*",  
                mappings=[  
                    InputFieldMappingEntry(name="chunk", source="/document/pages/*"),  
                    InputFieldMappingEntry(name="text_vector", source="/document/pages/*/text_vector"),  
                    InputFieldMappingEntry(name="title", source="/document/metadata_storage_name"),  
                ],  
            ),  
        ],  
        parameters=SearchIndexerIndexProjectionsParameters(  
            projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS  
        ),  
    ) 


    skills = [split_skill, embedding_skill]

    skillset = SearchIndexerSkillset(  
        name=skillset_name,  
        description="Skillset to chunk documents and generating embeddings",  
        skills=skills,  
        index_projection=index_projections,
    )
    
    client = SearchIndexerClient(endpoint=endpoint, credential=credential)  
    client.create_or_update_skillset(skillset)  
    print(f"{skillset.name} created")

    # Create an indexer
    indexer_name = f"{container_name}-indexer"
    data_source_name = f"{container_name}-connection"
    target_index_name = container_name

    indexer_parameters = None  # Define any indexer parameters if needed

    indexer = SearchIndexer(
        name=indexer_name,
        description="Indexer to index documents and generate embeddings",
        skillset_name=skillset_name,
        target_index_name=target_index_name,
        data_source_name=data_source_name,
        field_mappings=[
            FieldMapping(
                source_field_name="metadata_storage_name",
                target_field_name="title"
            )
        ],
        parameters=indexer_parameters
    )

    # Create or update the indexer
    indexer_result = indexer_client.create_or_update_indexer(indexer)
    print(f"Indexer '{indexer_name}' is created and running. Give the indexer a few minutes before running a query.")