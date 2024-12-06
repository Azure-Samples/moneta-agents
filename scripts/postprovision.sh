#!/bin/bash
set -e

echo "Running post-provision hook..."

openai_resource_id=$(
    az cognitiveservices account list \
      --query "[?properties.endpoint=='$AZURE_OPENAI_ENDPOINT'].{id:id}" \
      --output tsv
)

if [ -z "$openai_resource_id" ]; then
    echo "OpenAI resource with endpoint '$AZURE_OPENAI_ENDPOINT' not found"
    exit 1
fi

echo "Assigning role on OpenAI resource..."

echo "  to $AZURE_PRINCIPAL_ID..."
az role assignment create \
    --assignee "$AZURE_PRINCIPAL_ID" \
    --role "Cognitive Services OpenAI User" \
    --scope "$openai_resource_id"

echo "  to $AI_SEARCH_PRINCIPAL_ID..."
az role assignment create \
    --assignee "$AI_SEARCH_PRINCIPAL_ID" \
    --role "Cognitive Services OpenAI User" \
    --scope "$openai_resource_id"