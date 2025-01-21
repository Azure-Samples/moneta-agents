Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:DEBUG -match '^(1|yes|true)$') {
    Set-PSDebug -Trace 1
}

# Add here commands that need to be executed before provisioning
# Typically: preparing additional environment variables, creating app registrations, etc.
# see https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility

if ($env:WITH_AUTHENTICATION -eq "true") {
    Write-Host "    ➜ " -ForegroundColor Green -NoNewline
    Write-Host "Authentication was enabled deleting app registration..."

    $clientAppId = if ($env:AZURE_CLIENT_APP_ID) {
        $env:AZURE_CLIENT_APP_ID
    } else {
        "00000000-0000-0000-0000-000000000000"
    }

    try {
        $AZURE_APP_ID = az ad app show `
            --id $clientAppId `
            --query id `
            -o tsv 2>$null
    } catch {
        $AZURE_APP_ID = $null
    }

    if ($AZURE_APP_ID) {
        Write-Host "Deleting app $($env:AZURE_CLIENT_APP_ID)..."
        az ad app delete --id $AZURE_APP_ID
    }
}
