import json
import os
from typing import Annotated
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from semantic_kernel.functions import kernel_function

class CIOFacade:
    def __init__(self, service_endpoint, credential, index_name, semantic_configuration_name):
        self.semantic_configuration_name = semantic_configuration_name
        self.search_client = SearchClient(service_endpoint, index_name, credential)
        # self.search_client = SearchClient(service_endpoint, index_name, AzureKeyCredential(key))

    @kernel_function(
        name="search_cio", 
        description="Search details about investments researches, reccomandations, in house view from the CIO (Chief Investment Office)"
    )
    def search(self, query: Annotated[str,"The query to search for"]) -> Annotated[str, "The output in JSON format"]:
        
        text_vector_query = VectorizableTextQuery(
            kind="text",
            text=query,
            fields="text_vector"
        )

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

        response = list(results)

        output = []
        for result in response:
            result.pop("parent_id")
            result.pop("chunk_id")
            result.pop("text_vector")
            output.append(result)

        return json.dumps(output)