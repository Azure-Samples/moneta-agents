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

param logAnalyticsWorkspaceName string
// param applicationInsightsName string

// param azureOpenAIModelEndpoint string
// param azureModelDeploymentName string

// param cosmosDbEndpoint string
// param cosmosDbName string
// param cosmosDbContainer string

param exists bool

// resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31'  existing = { name: identityName }
// resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = { name: applicationInsightsName }
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = { name: logAnalyticsWorkspaceName }

module fetchLatestImage './fetch-container-image.bicep' = {
  name: '${name}-fetch-image'
  params: {
    exists: exists
    name: name
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2022-10-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    daprAIConnectionString: env.APPLICATIONINSIGHTS_CONNECTION_STRING
  }
}

resource app 'Microsoft.App/containerApps@2023-04-01-preview' = {
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
        external: true
        targetPort: 80
        transport: 'auto'
      }
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          identity: identityId
        }
      ]
      // secrets: [
      //   {
      //       name: 'api-key'
      //       value: '${openAIService.listKeys().key1}'
      //   }
      // ]
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
output id string = app.id
