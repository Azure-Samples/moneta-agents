#!/usr/bin/env pwsh

# Add here commands that need to be executed after provisioning
# Typically: loading data in databases, AI Search or storage accounts, etc.
# see https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility

if ($env:WITH_AUTHENTICATION -match "true") {
    Write-Host "  ➜ " -ForegroundColor Green -NoNewline
    Write-Host "Authentication is enabled updating login callback..."

    $redirect_uri = "$($env:SERVICE_FRONTEND_URL)/.auth/login/aad/callback"

    Write-Host "   Adding app registration redirect URI '$redirect_uri'..."
    az ad app update `
        --id $env:AZURE_CLIENT_APP_ID `
        --web-redirect-uris "http://localhost:5801/.auth/login/aad/callback" $redirect_uri `
        --output table

    # Remove the secret from the environment after it has been set in the keyvault
    azd env set AZURE_CLIENT_APP_SECRET ""
}
