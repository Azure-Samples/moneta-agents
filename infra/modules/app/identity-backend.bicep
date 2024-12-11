param identityName string
param location string

resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

output identityId string = appIdentity.id
output clientId string = appIdentity.properties.clientId
output principalId string = appIdentity.properties.principalId
output name string = appIdentity.name
