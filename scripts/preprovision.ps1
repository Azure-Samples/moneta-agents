#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'
if ($env:DEBUG -match '^1|yes|true$') {
    Set-PSDebug -Trace 2
}

if ($env:WITH_AUTHENTICATION -match "true") {
    Write-Host "    ➜ " -ForegroundColor Green -NoNewline
    Write-Host "Authentication is enabled creating app registration..."

    if (-not $env:AZURE_AUTH_TENANT_ID) {
        $env:AZURE_AUTH_TENANT_ID = az account show --query tenantId -o tsv
        Write-Host "    AZURE_AUTH_TENANT_ID not provided: Default to $($env:AZURE_AUTH_TENANT_ID) from AZ CLI" -ForegroundColor Yellow
    }
    azd env set AZURE_AUTH_TENANT_ID $env:AZURE_AUTH_TENANT_ID

    $app_name = "$($env:AZURE_ENV_NAME)-app"
    $current_user_upn = az ad signed-in-user show --query userPrincipalName -o tsv
    $current_user_id = az ad user show --id $current_user_upn --query id --output tsv
    $AZURE_CLIENT_APP_ID = az ad app list --display-name $app_name --query '[].appId' -o tsv

    Write-Host "    Current user          : $current_user_upn"
    Write-Host "    Current tenant        : $($env:AZURE_AUTH_TENANT_ID)"
    Write-Host "    App Registration name : $app_name"

    if (-not $AZURE_CLIENT_APP_ID) {
        Write-Host "    Creating app $app_name..."
        $azure_app_object_id = az ad app create `
            --display-name $app_name `
            --web-redirect-uris http://localhost:5801/ `
            --query id `
            --output tsv
        $AZURE_CLIENT_APP_ID = az ad app show --id $azure_app_object_id --query appId -o tsv

        az ad app update `
            --id $AZURE_CLIENT_APP_ID `
            --identifier-uris "api://$AZURE_CLIENT_APP_ID" `
            --enable-id-token-issuance true `
            --enable-access-token-issuance true `
            --required-resource-accesses @scripts/requiredResourceAccess.json

        $SERVICE_PRINCIPAL_ID = az ad sp create `
            --id $AZURE_CLIENT_APP_ID `
            --query id `
            --output tsv

        az ad app owner add `
            --id $AZURE_CLIENT_APP_ID `
            --owner-object-id $current_user_id

        $AZURE_CLIENT_APP_SECRET = az ad app credential reset `
            --id $AZURE_CLIENT_APP_ID `
            --display-name "client-secret" `
            --query password `
            --years 1 `
            --output tsv

        az rest `
            --method PATCH `
            --headers 'Content-Type=application/json' `
            --uri "https://graph.microsoft.com/v1.0/applications/$azure_app_object_id" `
            --body @scripts/oauth2PermissionScopes.json

        az rest `
            --method PATCH `
            --headers 'Content-Type=application/json' `
            --uri "https://graph.microsoft.com/v1.0/applications/$azure_app_object_id" `
            --body @scripts/preAuthorizedApplications.json

        azd env set AZURE_CLIENT_APP_SECRET $AZURE_CLIENT_APP_SECRET

        Write-Host "    App $app_name created with ID $AZURE_CLIENT_APP_ID and SP ID $SERVICE_PRINCIPAL_ID"
    }
    else {
        Write-Host "    App '$AZURE_CLIENT_APP_ID' already exists, skipping creation" -ForegroundColor Yellow
    }

    azd env set AZURE_CLIENT_APP_ID $AZURE_CLIENT_APP_ID

    Write-Host "    ➜ " -ForegroundColor Green -NoNewline
    Write-Host "Application registration $app_name ($AZURE_CLIENT_APP_ID) has been created."

    # Credits: inspired by https://gpiskas.com/posts/automate-creation-app-registration-azure-cli/#creating-and-modifying-the-app-registration
}
