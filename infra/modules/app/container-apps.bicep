metadata description = 'Creates an Azure Container App and deals with initial state when no container is deployed.'

@description('Name of the container app')
param name string

param location string = resourceGroup().location

param tags object = {}

@description('Environment variables for the container in key value pairs')
param env object = {}

@description('Resource ID of the identity to use for the container app')
param identityId string

@description('Name of the service the container app belongs to in azure.yaml')
param serviceName string

param containerRegistryName string

@description('Name of the container apps environment to build the app in')
param containerAppsEnvironmentName string

@description('The keyvault identities required for the container')
@secure()
param keyvaultIdentities object = {}

@description('The secrets required for the container')
@secure()
param secrets object = {}

@description('External Ingress Allowed?')
param externalIngressAllowed bool = true
// param applicationInsightsName string

// param azureOpenAIModelEndpoint string
// param azureModelDeploymentName string

// param cosmosDbEndpoint string
// param cosmosDbName string
// param cosmosDbContainer string

param exists bool


var keyvalueSecrets = [for secret in items(secrets): {
  name: secret.key
  value: secret.value
}]

var keyvaultIdentitySecrets = [for secret in items(keyvaultIdentities): {
  name: secret.key
  keyVaultUrl: secret.value.keyVaultUrl
  identity: secret.value.identity
}]

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' existing = { name: containerAppsEnvironmentName }

module fetchLatestImage './fetch-container-image.bicep' = {
  name: '${name}-fetch-image'
  params: {
    exists: exists
    name: name
  }
}

resource app 'Microsoft.App/containerApps@2024-08-02-preview' = {
  name: name
  location: location
  tags: union(tags, {'azd-service-name':  serviceName })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identityId}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress:  {
        external: externalIngressAllowed
        targetPort: 8000
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: [ 'https://portal.azure.com', 'https://ms.portal.azure.com' ]
        }
      }
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          identity: identityId
        }
      ]
      secrets: concat(keyvalueSecrets, keyvaultIdentitySecrets)
    }
    template: {
      containers: [
        {
          image: fetchLatestImage.outputs.?containers[?0].?image ?? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
          name: 'main'
          env: [
            for key in objectKeys(env): {
              name: key
              value: '${env[key]}'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2.0Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}

output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
output name string = app.name
output URL string = 'https://${app.properties.configuration.ingress.fqdn}'
output internalUrl string = 'http://${app.name}'
output id string = app.id
