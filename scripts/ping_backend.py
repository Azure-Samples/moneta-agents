# Use DefaultAzureCredential to authenticate
# Then do an http post request with a json body
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv
import json
import os
import requests
from subprocess import run, PIPE
from io import StringIO

import asyncio


def get_token_via_graph(credential):
    from msgraph_beta import GraphServiceClient
    from msgraph_beta.generated.applications.applications_request_builder import ApplicationsRequestBuilder
    from kiota_abstractions.base_request_configuration import RequestConfiguration
    graph_client = GraphServiceClient(credential)

    query_params = ApplicationsRequestBuilder.ApplicationsRequestBuilderGetQueryParameters(
            filter = f"web/homePageUrl eq '{base_url}'",
            count = True,
            top = 1,
            orderby = ["displayName"],
    )

    request_configuration = RequestConfiguration(
    query_parameters = query_params,
    )
    request_configuration.headers.add("ConsistencyLevel", "eventual")


    application_response = asyncio.run(graph_client.applications.get(request_configuration = request_configuration))

    return credential.get_token(f"{application_response.value[0].identifier_uris[0]}/.default", )

if __name__ == "__main__":
    result = run("azd env get-values", stdout=PIPE, stderr=PIPE, shell=True, text=True)
    if result.returncode != 0:
        raise Exception("azd env get-values failed")
    load_dotenv(stream=StringIO(result.stdout), override=True)


    base_url = os.getenv('SERVICE_BACKEND_URL')
    url = f"{os.getenv('SERVICE_BACKEND_URL')}/http_trigger"

    credential = DefaultAzureCredential()

    url = f"{os.getenv('SERVICE_BACKEND_URL')}/http_trigger"
    #token = get_token_via_graph(credential)
    token = credential.get_token(f"{os.getenv('SERVICE_BACKEND_URL')}/.default", )

    data = {
        "user_id": "123",
        "chat_id": "456",
        "message": "Hello",
        "load_history": True,
        "use_case": "fsi_insurance"
    }
    headers = {
        'Authorization': f"Bearer {token.token}",
    }
    with requests.post(f"{base_url}/http_trigger", headers=headers, json=data, stream=True) as response:
        response.raise_for_status()
        print(response.text)


