# If you get cosmosdb auth error due to local auth disabled and need AAD token to authorize reqeusts:
resourceGroupName="<your res group where you have your cosmosdb>"
accountName="<your cosmosdb account name>"
principalId="<your azure principal id>"

# Retrieve the scope (ensure variables are referenced correctly)
scope=$(
    az cosmosdb show \
        --resource-group "$resourceGroupName" \
        --name "$accountName" \
        --query id \
        --output tsv
)

# Use the scope variable (prefix with '$')
az cosmosdb sql role assignment create \
    --resource-group "$resourceGroupName" \
    --account-name "$accountName" \
    --role-definition-name "Cosmos DB Built-in Data Contributor" \
    --principal-id $principalId \
    --scope "$scope"

az cosmosdb sql role assignment create \
    --resource-group "$resourceGroupName" \
    --account-name "$accountName" \
    --role-definition-name "Cosmos DB Built-in Data Reader" \
    --principal-id $principalId \
    --scope "$scope"