#!/bin/bash -x
set -e

echo "Running postprovision hook..."

REDIRECT_URI="$SERVICE_FRONTEND_URL/.auth/login/aad/callback"

# echo "Adding app registration redirect URI $REDIRECT_URI..."
# az ad app update \
#     --id "$AZURE_CLIENT_APP_ID" \
#     --web-redirect-uris "http://localhost:5801/.auth/login/aad/callback" "$REDIRECT_URI" \
#     --identifier-uris "api://$AZURE_CLIENT_APP_ID" "$SERVICE_BACKEND_URL" \
#     --output table

az ad app update \
    --id "$AZURE_CLIENT_APP_ID" \
    --web-redirect-uris "http://localhost:5801/.auth/login/aad/callback" "$REDIRECT_URI" \
    --output table