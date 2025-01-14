param name string
param location string = resourceGroup().location
param tags object = {}

param adminUserEnabled bool = true
param anonymousPullEnabled bool = false
param dataEndpointEnabled bool = false
param encryption object = {
  status: 'disabled'
}
param networkRuleBypassOptions string = 'AzureServices'
param publicNetworkAccess string = 'Enabled'
param sku object = {
  name: 'Standard'
}
param zoneRedundancy string = 'Disabled'

param pullingIdentityNames array = []

// 2022-02-01-preview needed for anonymousPullEnabled
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2022-02-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: sku
  properties: {
    adminUserEnabled: adminUserEnabled
    anonymousPullEnabled: anonymousPullEnabled
    dataEndpointEnabled: dataEndpointEnabled
    encryption: encryption
    networkRuleBypassOptions: networkRuleBypassOptions
    publicNetworkAccess: publicNetworkAccess
    zoneRedundancy: zoneRedundancy
  }
}

resource identities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = [for identityName in pullingIdentityNames: {
  name: identityName
  location: location
}]

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for i in range(0, length(pullingIdentityNames)): {
  scope: containerRegistry
  name: guid(subscription().id, resourceGroup().id, identities[i].id, 'acrPullRole')
  properties: {
    roleDefinitionId:  subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalType: 'ServicePrincipal'
    principalId: identities[i].properties.principalId
  }
}]


/* -------------------------------------------------------------------------- */
/*                                   OUTPUTS                                  */
/* -------------------------------------------------------------------------- */

@description('The resource ID of the key vault.')
output resourceId string = containerRegistry.id

output loginServer string = containerRegistry.properties.loginServer

output name string = containerRegistry.name
