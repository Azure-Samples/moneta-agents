#!/bin/bash
set -e 

echo "Running preprovision hook..."

if [ -z "$AZURE_AUTH_TENANT_ID" ]; then
     echo -e "\e[3;31mAZURE_AUTH_TENANT_ID note provided: Defaulting to tenant in which AZ CLI is logged in\e[0m"
    AZURE_AUTH_TENANT_ID=$(az account show --query tenantId -o tsv)
fi
azd env set AZURE_AUTH_TENANT_ID "$AZURE_AUTH_TENANT_ID"

APP_NAME="$AZURE_ENV_NAME-app"
CURRENT_USER_UPN=$(az ad signed-in-user show --query userPrincipalName -o tsv)
CURRENT_USER_ID=$(az ad user show --id "$CURRENT_USER_UPN" --query id --output tsv)

echo "Current user   : $CURRENT_USER_UPN"
echo "Current tenant : $AZURE_AUTH_TENANT_ID"

if [ -z "$(az ad app list --app-id "${AZURE_CLIENT_APP_ID=00000000-0000-0000-0000-000000000000}" --query '[].id' -o tsv)" ];
then
    echo "Creating app $APP_NAME..."
    AZURE_APP_ID=$(
        az ad app create \
            --display-name "$APP_NAME" \
            --web-redirect-uris http://localhost:5801/ \
            --query id \
            --output tsv
    )
    AZURE_CLIENT_APP_ID=$(
        az ad app show --id $AZURE_APP_ID --query appId -o tsv
    )

    az ad app update \
        --id $AZURE_CLIENT_APP_ID \
        --identifier-uris "api://$AZURE_CLIENT_APP_ID" \
        --enable-id-token-issuance true \
        --enable-access-token-issuance true \
        --required-resource-accesses @scripts/requiredResourceAccess.json

    SERVICE_PRINCIPAL_ID=$(
        az ad sp create \
            --id "$AZURE_CLIENT_APP_ID" \
            --query id \
            --output tsv
    )

    az ad app owner add \
        --id "$AZURE_CLIENT_APP_ID" \
        --owner-object-id "$CURRENT_USER_ID"

    AZURE_CLIENT_APP_SECRET=$(
        az ad app credential reset \
            --id $AZURE_CLIENT_APP_ID \
            --display-name "client-secret" \
            --query password \
            --years 1 \
            --output tsv 
    )

    az rest \
        --method PATCH \
        --headers 'Content-Type=application/json' \
        --uri "https://graph.microsoft.com/v1.0/applications/$AZURE_APP_ID" \
        --body @scripts/oauth2PermissionScopes.json

    az rest \
        --method PATCH \
        --headers 'Content-Type=application/json' \
        --uri "https://graph.microsoft.com/v1.0/applications/$AZURE_APP_ID" \
        --body @scripts/preAuthorizedApplications.json

    azd env set AZURE_CLIENT_APP_SECRET "$AZURE_CLIENT_APP_SECRET"
    azd env set AZURE_CLIENT_APP_ID     "$AZURE_CLIENT_APP_ID"

    echo "App $APP_NAME created with ID $AZURE_CLIENT_APP_ID and SP ID $SERVICE_PRINCIPAL_ID"
else
    echo "App $AZURE_CLIENT_APP_ID already exists, skipping creation"
fi

# Credits: inspired by https://gpiskas.com/posts/automate-creation-app-registration-azure-cli/#creating-and-modifying-the-app-registration