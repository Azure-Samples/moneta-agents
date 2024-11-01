var functionAppDockerImage = 'DOCKER|moneta.azurecr.io/moneta-ai-backend:v1.1.4' 
var webappAppDockerImage = 'DOCKER|moneta.azurecr.io/moneta-ai-frontend:v1.1.3'

@description('Name of the Resource Group')
param resourceGroupName string = resourceGroup().name

@description('Location for all resources')
param location string = resourceGroup().location

@description('Name prefix for all resources')
param namePrefix string = 'moneta'

@description('Name of the Cosmos DB account')
param cosmosDbAccountName string = toLower('cdb${uniqueString(resourceGroup().id)}')

@description('Name of the Cosmos DB database')
param cosmosDbDatabaseName string = 'rminsights'

@description('Name of the Cosmos DB container for insurance')
param cosmosDbInsuranceContainerName string = 'user_fsi_ins_data'

@description('Name of the Cosmos DB container for banking')
param cosmosDbBankingContainerName string = 'user_fsi_bank_data'

@description('Name of the Cosmos DB container for CRM data')
param cosmosDbCRMContainerName string = 'clientdata'

// Define the storage account name
param storageAccountName string = 'sa${uniqueString(resourceGroup().id)}'

@description('Name of the Function App')
param functionAppName string = toLower('func${uniqueString(resourceGroup().id)}')

@description('Application Insights Location')
param appInsightsLocation string = location

// New parameters for Azure OpenAI
@description('Azure OpenAI Endpoint')
param AZURE_OPENAI_ENDPOINT string

@description('Azure OpenAI Key')
@secure()
param AZURE_OPENAI_KEY string

@description('Azure OpenAI Model')
param AZURE_OPENAI_DEPLOYMENT_NAME string

@description('Azure OpenAI API Version')
param AZURE_OPENAI_API_VERSION string = '2024-06-01'

// Optional parameters to override AI Search settings
@description('Override AI Search Endpoint (optional)')
param overrideAiSearchEndpoint string = ''

@description('Override AI Search Key (optional)')
@secure()
param overrideAiSearchKey string = ''

// Variables for AI Search index names and configurations
var aiSearchCioIndexName = 'cio-index'
var aiSearchCioSemanticConfiguration = 'cio-semantic-config'
var aiSearchFundsIndexName = 'funds-index'
var aiSearchFundsSemanticConfiguration = 'funds-semantic-config'
var aiSearchInsIndexName = 'ins-index'
var aiSearchInsSemanticConfiguration = 'ins-semantic-config'
var aiSearchVectorFieldName = 'contentVector'

// Define common tags  
var commonTags = {  
  solution: 'moneta-agentic-gbb-ai-1.0'    
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2021-06-01' = {  
  name: 'logAnalyticsWorkspace'  
  location: location  
  properties: {  
    retentionInDays: 30  
  }  
  tags: commonTags
}  

// Application Insights instance
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${functionAppName}-ai'
  location: appInsightsLocation
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// Cosmos DB Account
resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2022-08-15' = {
  name: cosmosDbAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    capabilities: []
    ipRules: []
    isVirtualNetworkFilterEnabled: false
    enableAutomaticFailover: false
    enableFreeTier: false
    enableAnalyticalStorage: false
    cors: []
  }
  tags: commonTags
}

// Cosmos DB Database
resource cosmosDbDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2022-05-15' = {
  parent: cosmosDbAccount
  name: cosmosDbDatabaseName
  properties: {
    resource: {
      id: cosmosDbDatabaseName
    }
    options: {}
  }
  tags: commonTags
}

// Cosmos DB Containers
resource cosmosDbInsuranceContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2022-05-15' = {
  parent: cosmosDbDatabase
  name: cosmosDbInsuranceContainerName
  properties: {
    resource: {
      id: cosmosDbInsuranceContainerName
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: []
      }
    }
    options: {}
  }
  tags: commonTags
}

resource cosmosDbBankingContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2022-05-15' = {
  parent: cosmosDbDatabase
  name: cosmosDbBankingContainerName
  properties: {
    resource: {
      id: cosmosDbBankingContainerName
      partitionKey: {
        paths: ['/user_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: []
      }
    }
    options: {}
  }
  tags: commonTags
}

resource cosmosDbCRMContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2022-05-15' = {
  parent: cosmosDbDatabase
  name: cosmosDbCRMContainerName
  properties: {
    resource: {
      id: cosmosDbCRMContainerName
      partitionKey: {
        paths: ['/client_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: []
      }
    }
    options: {}
  }
  tags: commonTags
}

// Service Plan for Function App
resource servicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${functionAppName}-plan'
  location: location
  kind: 'Linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  properties: {
    reserved: true
  }
  tags: commonTags
}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
  }
  tags: commonTags
}

// Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2022-05-01' = {
  parent: storageAccount
  name: 'default'
}

// AI Search Service (Azure Cognitive Search)
resource aiSearchService 'Microsoft.Search/searchServices@2020-08-01' = if (empty(overrideAiSearchEndpoint)) {
  name: toLower('search${uniqueString(resourceGroup().id)}')
  location: location
  sku: {
    name: 'free'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
  }
  tags: commonTags
}

// Get AI Search admin key
var aiSearchAdminKey = empty(overrideAiSearchKey) ? listAdminKeys(aiSearchService.id, '2020-08-01').primaryKey : overrideAiSearchKey

// Set AI Search endpoint
var aiSearchEndpoint = empty(overrideAiSearchEndpoint) ? 'https://${aiSearchService.name}.search.windows.net' : overrideAiSearchEndpoint

// Function App with Managed Identity
resource functionApp 'Microsoft.Web/sites@2022-03-01' = {
  name: functionAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  kind: 'functionapp'
  properties: {
    serverFarmId: servicePlan.id
    httpsOnly: true
    siteConfig: {
      pythonVersion: '3.11'
      linuxFxVersion: functionAppDockerImage
      alwaysOn: true
      appSettings: [ 
        {
          name: 'AzureWebJobsStorage__credential'
          value: 'managedidentity'  
        } 
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AzureWebJobsFeatureFlags'
          value: 'EnableWorkerIndexing'
        }
        {
          name: 'AzureWebJobsStorage__serviceUri'
          value: 'https://${storageAccount.name}.blob.core.windows.net'  
        }  
        {
          name: 'AzureWebJobsStorage__blobServiceUri'
          value: 'https://${storageAccount.name}.blob.core.windows.net'  
        }
        {
          name: 'AzureWebJobsStorage__queueServiceUri'
          value: 'https://${storageAccount.name}.queue.core.windows.net'  
        }
        {
          name: 'AzureWebJobsStorage__tableServiceUri'
          value: 'https://${storageAccount.name}.table.core.windows.net'  
        }              
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_WORKER_PROCESS_COUNT'
          value: '1'
        }
        {
          name: 'WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT'
          value: '1'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://index.docker.io'
        }              
        {
          name: 'COSMOSDB_ENDPOINT'
          value: cosmosDbAccount.properties.documentEndpoint
        }
        {
          name: 'COSMOSDB_DATABASE_NAME'
          value: cosmosDbDatabaseName
        }
        {
          name: 'COSMOSDB_CONTAINER_FSI_BANK_USER_NAME'
          value: cosmosDbBankingContainerName
        }
        {
          name: 'COSMOSDB_CONTAINER_FSI_INS_USER_NAME'
          value: cosmosDbInsuranceContainerName
        }
        {
          name: 'COSMOSDB_CONTAINER_CLIENT_NAME'
          value: cosmosDbCRMContainerName
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: AZURE_OPENAI_ENDPOINT
        }
        {
          name: 'AZURE_OPENAI_KEY'
          value: AZURE_OPENAI_KEY
        }
        {
          name: 'AZURE_OPENAI_MODEL'
          value: AZURE_OPENAI_DEPLOYMENT_NAME
        }
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: AZURE_OPENAI_API_VERSION
        }
        {
          name: 'AI_SEARCH_ENDPOINT'
          value: aiSearchEndpoint
        }
        {
          name: 'AI_SEARCH_KEY'
          value: aiSearchAdminKey
        }
        {
          name: 'AI_SEARCH_CIO_INDEX_NAME'
          value: aiSearchCioIndexName
        }
        {
          name: 'AI_SEARCH_CIO_SEMANTIC_CONFIGURATION'
          value: aiSearchCioSemanticConfiguration
        }
        {
          name: 'AI_SEARCH_FUNDS_INDEX_NAME'
          value: aiSearchFundsIndexName
        }
        {
          name: 'AI_SEARCH_FUNDS_SEMANTIC_CONFIGURATION'
          value: aiSearchFundsSemanticConfiguration
        }
        {
          name: 'AI_SEARCH_INS_INDEX_NAME'
          value: aiSearchInsIndexName
        }
        {
          name: 'AI_SEARCH_INS_SEMANTIC_CONFIGURATION'
          value: aiSearchInsSemanticConfiguration
        }
        {
          name: 'AI_SEARCH_VECTOR_FIELD_NAME'
          value: aiSearchVectorFieldName
        }
      ]
    }
  }
  tags: commonTags
}

// Role assignments for the Function App's managed identity
resource functionAppStorageBlobDataContributorRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(functionApp.id, storageAccount.id, 'StorageBlobDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionAppStorageBlobDataOwnerRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(functionApp.id, storageAccount.id, 'StorageBlobDataOwner')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b') // Storage Blob Data Owner
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionAppStorageQueueDataContributorRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(functionApp.id, storageAccount.id, 'StorageQueueDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88') // Storage Queue Data Contributor
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionAppStorageAccountContributorRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(functionApp.id, storageAccount.id, 'StorageAccountContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a84-46fb-8f53-869881c3d3ab') // Storage Account Contributor
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cosmos DB Role Assignments
resource cosmosDbRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: cosmosDbAccount
  name: 'b24988ac-6180-42a0-ab88-20f7382dd24c' // Built-in role: Cosmos DB Account Reader Role
}

resource cosmosDbRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(subscription().id, cosmosDbAccount.id, functionApp.id, cosmosDbRoleDefinition.id)
  scope: cosmosDbAccount
  properties: {
    principalId: functionApp.identity.principalId
    roleDefinitionId: cosmosDbRoleDefinition.id
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    functionApp
  ]
}

resource cosmosDbDataContributorRoleDefinition 'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions@2021-04-15' existing = {
  parent: cosmosDbAccount
  name: '00000000-0000-0000-0000-000000000002' // Built-in Data Contributor Role
}

resource cosmosDbDataContributorRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2021-04-15' = {
  parent: cosmosDbAccount
  name: guid(cosmosDbAccount.id, functionApp.id, cosmosDbDataContributorRoleDefinition.id)
  properties: {
    roleDefinitionId: cosmosDbDataContributorRoleDefinition.id
    principalId: functionApp.identity.principalId
    scope: cosmosDbAccount.id
  }
}

// App Service Plan for Streamlit
@description('Name of the App Service Plan for Streamlit')
param appServicePlanName string = '${namePrefix}-plan'

@description('Name of the Web App for Streamlit')
param webAppName string = '${namePrefix}-agents'

// Streamlit App Service Plan
resource streamlitServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: appServicePlanName
  location: location
  kind: 'Linux'
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  properties: {
    reserved: true
  }
  tags: commonTags
}

// Streamlit Web App
resource streamlitWebApp 'Microsoft.Web/sites@2022-03-01' = {
  name: webAppName
  location: location
  properties: {
    serverFarmId: streamlitServicePlan.id
    siteConfig: {
      linuxFxVersion: webappAppDockerImage
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'FUNCTION_APP_URL'
          value: 'https://${functionApp.properties.defaultHostName}'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://index.docker.io'
        } 
        {
          name: 'DISABLE_LOGIN'
          value: 'False'
        }
        {
          name: 'AZ_TENANT_ID'
          value: ''
        }  
        {
          name: 'AZ_REG_APP_CLIENT_ID'
          value: ''
        }    
        {
          name: 'AZ_REG_APP_SCOPE'
          value: 'User.Read'
        } 
        {
          name: 'WEB_REDIRECT_URI'
          value: ''
        } 
        {
          name: 'FUNCTION_APP_KEY'
          value: listKeys('${resourceId('Microsoft.Web/sites', functionAppName)}/host/default', '2018-11-01').functionKeys.default
        } 
      ]
    }
    httpsOnly: true
  }
  kind: 'app,linux'
  tags: commonTags
}
