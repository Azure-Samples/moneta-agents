#!/bin/bash
set -e

echo "Running post-provision hook..."

openai_resource_id=$(
    az cognitiveservices account list \
      --query "[?properties.endpoint=='$AZURE_OPENAI_ENDPOINT'].{id:id}" \
      --output tsv
)
cosmosdb_resource_id=$(
    az cosmosdb show \
        --resource-group "$AZURE_RESOURCE_GROUP" \
        --name "$COSMOSDB_ACCOUNT_NAME" \
        --query id \
        --output tsv
)
    
if [ -z "$openai_resource_id" ]; then
    echo "OpenAI resource with endpoint '$AZURE_OPENAI_ENDPOINT' not found!"
    exit 1
fi

if [ -z "$cosmosdb_resource_id" ]; then
    echo "Cosmos DB resource with account name '$COSMOSDB_ACCOUNT_NAME' not found in resource group '$AZURE_RESOURCE_GROUP'!"
    exit 1
fi

echo "Assigning role on OpenAI resource..."
az role assignment create -o table \
    --assignee "$AZURE_PRINCIPAL_ID" \
    --role "Cognitive Services OpenAI User" \
    --scope "$openai_resource_id" 

az role assignment create -o table \
    --assignee "$AI_SEARCH_PRINCIPAL_ID" \
    --role "Cognitive Services OpenAI User" \
    --scope "$openai_resource_id"

echo "Assigning role on Cosmos DB resource..."
az cosmosdb sql role assignment create \
    --resource-group "$AZURE_RESOURCE_GROUP" \
    --account-name "$COSMOSDB_ACCOUNT_NAME" \
    --role-definition-name "Cosmos DB Built-in Data Contributor" \
    --principal-id $AZURE_PRINCIPAL_ID \
    --scope "$cosmosdb_resource_id"

python ./scripts/data_upload.py
python ./scripts/data_indexing.py