/* -------------------------------------------------------------------------- */
/*                                 PARAMETERS                                 */
/* -------------------------------------------------------------------------- */

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@description('Principal ID of the user runing the deployment')
param azurePrincipalId string

@description('Extra tags to be applied to provisioned resources')
param extraTags object = {}

/* ---------------------------- Shared Resources ---------------------------- */

@maxLength(50)
@description('Name of the container registry to deploy. If not specified, a name will be generated. The name is global and must be unique within Azure. The maximum length is 50 characters.')
param containerRegistryName string = ''

/* --------------------------------- Backend -------------------------------- */

@maxLength(32)
@description('Name of the backend container app to deploy. If not specified, a name will be generated. The maximum length is 32 characters.')
param backendContainerAppName string = ''

@description('Set if the backend container app already exists.')
param backendAppExists bool = false



/* -------------------------------------------------------------------------- */


var functionAppDockerImage = 'DOCKER|moneta.azurecr.io/moneta-ai-backend:v1.1.6' 
var webappAppDockerImage = 'DOCKER|moneta.azurecr.io/moneta-ai-frontend:v1.1.6'

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
param azureOpenaiEndpoint string

@description('Azure OpenAI Key')
@secure()
param azureOpenaiKey string

@description('Azure OpenAI Model')
param azureOpenaiDeploymentName string

@description('Azure OpenAI embedding model deployment name')
param azureOpenaiEmbeddingModelName string = 'text-embedding-3-large'

@description('Azure OpenAI API Version')
param azureOpenaiApiVersion string = '2024-06-01'

// Optional parameters to override AI Search settings
@description('Override AI Search Endpoint (optional)')
param overrideAiSearchEndpoint string = ''

@description('Override AI Search Key (optional)')
@secure()
param overrideAiSearchKey string = ''



/* -------------------------------------------------------------------------- */
/*                                  VARIABLES                                 */
/* -------------------------------------------------------------------------- */

// Load abbreviations from JSON file
var abbreviations = loadJsonContent('./abbreviations.json')

@description('Generate a unique token to make global resource names unique')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

@description('Name of the environment with only alphanumeric characters. Used for resource names that require alphanumeric characters only')
var alphaNumericEnvironmentName = replace(replace(environmentName, '-', ''), ' ', '')

/* --------------------- Globally Unique Resource Names --------------------- */

var _containerRegistryName = !empty(containerRegistryName) ? containerRegistryName : take('${abbreviations.containerRegistryRegistries}${take(alphaNumericEnvironmentName, 35)}${resourceToken}', 50)

/* ----------------------------- Resource Names ----------------------------- */

var _backendContainerAppName = !empty(backendContainerAppName) ? backendContainerAppName : take('${abbreviations.appContainerApps}backend-${environmentName}', 32)


// Variables for AI Search index names and configurations
var aiSearchCioIndexName = 'cio-index'
var aiSearchCioSemanticConfiguration = 'cio-semantic-config'
var aiSearchFundsIndexName = 'funds-index'
var aiSearchFundsSemanticConfiguration = 'funds-semantic-config'
var aiSearchInsIndexName = 'ins-index'
var aiSearchInsSemanticConfiguration = 'ins-semantic-config'
var aiSearchVectorFieldName = 'contentVector'

// Define common tags  
var tags = union({  
 'azd-env-name': environmentName
  solution: 'moneta-agentic-gbb-ai-1.0'    
}, extraTags)



/* -------------------------------------------------------------------------- */
/*                                  RESOURCES                                 */
/* -------------------------------------------------------------------------- */

module backendAppIdentity './modules/app/identity.bicep' = {
  name: 'backendAppIdentity'
  scope: resourceGroup()
  params: {
    location: location
    identityName: _backendContainerAppName
  }
}

module containerRegistry 'modules/app/registry.bicep' = {
  name: 'registry'
  scope: resourceGroup()
  params: {
    location: location
    identityName: backendAppIdentity.outputs.name
    tags: tags
    name: '${abbreviations.containerRegistryRegistries}${resourceToken}'
  }
}

module backendApp 'modules/app/containerapp.bicep' = {
  name: 'backend-container-app'
  scope: resourceGroup()
  params: {
    name: _backendContainerAppName
    tags: tags
    logAnalyticsWorkspaceName: logAnalytics.name
    identityId: backendAppIdentity.outputs.identityId
    containerRegistryName: containerRegistry.outputs.name
    exists: backendAppExists
    serviceName: 'backend'
    env: {
      AI_SEARCH_CIO_INDEX_NAME: aiSearchCioIndexName
      AI_SEARCH_ENDPOINT: aiSearchEndpoint
      AI_SEARCH_FUNDS_INDEX_NAME: aiSearchFundsIndexName
      AI_SEARCH_INS_INDEX_NAME: aiSearchInsIndexName
      AI_SEARCH_INS_SEMANTIC_CONFIGURATION: aiSearchInsSemanticConfiguration
      AI_SEARCH_KEY: aiSearchAdminKey
      AZURE_OPENAI_API_VERSION: azureOpenaiApiVersion
      AZURE_OPENAI_DEPLOYMENT: azureOpenaiDeploymentName
      AZURE_OPENAI_ENDPOINT: azureOpenaiEndpoint
      AZURE_OPENAI_KEY: azureOpenaiKey
      COSMOSDB_CONTAINER_CLIENT_NAME: cosmosDbCRMContainerName
      COSMOSDB_CONTAINER_FSI_BANK_USER_NAME: cosmosDbBankingContainerName
      COSMOSDB_CONTAINER_FSI_INS_USER_NAME: cosmosDbInsuranceContainerName
      COSMOSDB_DATABASE_NAME: cosmosDbDatabaseName
      COSMOSDB_ENDPOINT: cosmosDbAccount.properties.documentEndpoint
      HANDLER_TYPE: 'semantickernel'

      // required for container app daprAI
      APPLICATIONINSIGHTS_CONNECTION_STRING: appInsights.properties.ConnectionString

      // required for managed identity
      AZURE_CLIENT_ID: backendAppIdentity.outputs.clientId
    }
  }
}

resource backendAppStorageBlobDataContributorRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageAccount.id, _backendContainerAppName, 'StorageBlobDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: backendAppIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendAppStorageBlobDataOwnerRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageAccount.id, _backendContainerAppName, 'StorageBlobDataOwner')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b') // Storage Blob Data Owner
    principalId: backendAppIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendAppStorageQueueDataContributorRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageAccount.id, _backendContainerAppName, 'StorageQueueDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88') // Storage Queue Data Contributor
    principalId: backendAppIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource backendAppStorageAccountContributorRole 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageAccount.id, _backendContainerAppName, 'StorageAccountContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a84-46fb-8f53-869881c3d3ab') // Storage Account Contributor
    principalId: backendAppIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

// Cosmos DB Role Assignments
resource cosmosDbRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: cosmosDbAccount
  name: 'b24988ac-6180-42a0-ab88-20f7382dd24c' // Built-in role: Cosmos DB Account Reader Role
}

resource cosmosDbRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(cosmosDbAccount.id, _backendContainerAppName, cosmosDbRoleDefinition.id)
  scope: cosmosDbAccount
  properties: {
    principalId: backendAppIdentity.outputs.principalId
    roleDefinitionId: cosmosDbRoleDefinition.id
    principalType: 'ServicePrincipal'
  }
}

resource cosmosDbDataContributorRoleDefinition 'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions@2021-04-15' existing = {
  parent: cosmosDbAccount
  name: '00000000-0000-0000-0000-000000000002' // Built-in Data Contributor Role
}

resource cosmosDbDataContributorRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2021-04-15' = {
  parent: cosmosDbAccount
  name: guid(cosmosDbAccount.id, _backendContainerAppName, cosmosDbDataContributorRoleDefinition.id)
  properties: {
    roleDefinitionId: cosmosDbDataContributorRoleDefinition.id
    principalId: backendAppIdentity.outputs.principalId
    scope: cosmosDbAccount.id
  }
}



/* -------------------------------------------------------------------------- */

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2021-06-01' = {  
  name: 'logAnalyticsWorkspace'  
  location: location  
  properties: {  
    retentionInDays: 30  
  }  
  tags: tags
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
  tags: tags
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
  tags: tags
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
  tags: tags
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
  tags: tags
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
  tags: tags
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
  tags: tags
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
  tags: tags
}

// Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2022-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'aiSearchService'
  location: location
}

// AI Search Service (Azure Cognitive Search)
resource aiSearchService 'Microsoft.Search/searchServices@2024-06-01-preview' = if (empty(overrideAiSearchEndpoint)) {
  name: toLower('search${uniqueString(resourceGroup().id)}')
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
  }
  tags: tags
}

// Get AI Search admin key
var aiSearchAdminKey = empty(overrideAiSearchKey) ? listAdminKeys(aiSearchService.id, '2020-08-01').primaryKey : overrideAiSearchKey

// Set AI Search endpoint
var aiSearchEndpoint = empty(overrideAiSearchEndpoint) ? 'https://${aiSearchService.name}.search.windows.net' : overrideAiSearchEndpoint

// App Service Plan for Streamlit
@description('Name of the App Service Plan for Streamlit')
param appServicePlanName string = '${namePrefix}-plan'

@description('Name of the Web App for Streamlit')
param webAppName string = '${namePrefix}-agents-${uniqueString(resourceGroup().id)}'

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
  tags: tags
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
          value: backendApp.outputs.URL
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
        // TODO: handle authentication of the frontend to the backend app !!!
        /* 
        {
          name: 'FUNCTION_APP_KEY'
          value: listKeys('${resourceId('Microsoft.Web/sites', functionAppName)}/host/default', '2018-11-01').functionKeys.default
        } 
        */
      ]
    }
    httpsOnly: true
  }
  kind: 'app,linux'
  tags: tags
}

import * as role from './role.bicep'

resource userDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, azurePrincipalId, 'Storage Blob Data Contributor')
  scope: storageAccount
  properties: {
    principalId: azurePrincipalId
    roleDefinitionId: role.definitionId('Storage Blob Data Contributor')
  }
}

resource aisearchDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, identity.id, 'Storage Blob Data Contributor')
  scope: storageAccount
  properties: {
    principalId: identity.properties.principalId
    roleDefinitionId: role.definitionId('Storage Blob Data Contributor')
  }
}

resource userSearchIndexDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiSearchService.id, azurePrincipalId, 'Search Index Data Contributor')
  scope: aiSearchService
  properties: {
    principalId: azurePrincipalId
    roleDefinitionId: role.definitionId('Search Index Data Contributor')
  }
}

resource userSearchServiceContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiSearchService.id, azurePrincipalId, 'Search Service Contributor')
  scope: aiSearchService
  properties: {
    principalId: azurePrincipalId
    roleDefinitionId: role.definitionId('Search Service Contributor')
  }
}

/* -------------------------------------------------------------------------- */
/*                                   OUTPUTS                                  */
/* -------------------------------------------------------------------------- */

// Outputs are automatically saved in the local azd environment .env file.
// To see these outputs, run `azd env get-values`,  or `azd env get-values --output json` for json output.
// To generate your own `.env` file run `azd env get-values > .env`
// To use set these outputs as environment variables in your shell run `source <(azd env get-values | sed 's/^/export /')`

@description('The endpoint of the container registry.') // necessary for azd deploy
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer

/* -------------------------------------------------------------------------- */


output AI_SEARCH_ENDPOINT string = aiSearchEndpoint
output AI_SEARCH_PRINCIPAL_ID string = identity.properties.principalId
output AI_SEARCH_IDENTITY_ID string = identity.id
output AZURE_OPENAI_API_VERSION string = azureOpenaiApiVersion
output AZURE_OPENAI_DEPLOYMENT_NAME string = azureOpenaiDeploymentName
output AZURE_OPENAI_ENDPOINT string = azureOpenaiEndpoint
output AZURE_OPENAI_MODEL string = azureOpenaiDeploymentName
output AZURE_PRINCIPAL_ID string = azurePrincipalId
output FUNCTION_APP_NAME string = functionAppName
output COSMOSDB_ACCOUNT_NAME string = cosmosDbAccountName
output COSMOSDB_ENDPOINT string = cosmosDbAccount.properties.documentEndpoint
output COSMOSDB_DATABASE_NAME string = cosmosDbDatabaseName
output COSMOSDB_CONTAINER_CLIENT_NAME string = cosmosDbCRMContainerName
output COSMOSDB_CONTAINER_FSI_BANK_USER_NAME string = cosmosDbBankingContainerName
output COSMOSDB_CONTAINER_FSI_INS_USER_NAME string = cosmosDbInsuranceContainerName
output AZURE_OPENAI_EMBEDDING_MODEL_NAME string = azureOpenaiEmbeddingModelName
output AZURE_OPENAI_EMBEDDING_DIMENSIONS string = '1536'
output CHUNK_SIZE string = '2000'

output AI_SEARCH_CIO_INDEX_NAME string = 'moneta-cio-vector'
output AI_SEARCH_CIO_SEMANTIC_CONFIGURATION string = 'default'
output AI_SEARCH_FUNDS_INDEX_NAME string = 'moneta-funds-vector'
output AI_SEARCH_FUNDS_SEMANTIC_CONFIGURATION string = 'default'

output AI_SEARCH_INS_INDEX_NAME string = aiSearchInsIndexName
output AI_SEARCH_INS_SEMANTIC_CONFIGURATION string = aiSearchInsSemanticConfiguration

output AI_SEARCH_VECTOR_FIELD_NAME string = aiSearchVectorFieldName

// TODO: avoid outputting keys by using users's identity when running locally
output AZURE_OPENAI_KEY string = azureOpenaiKey 
output AZURE_SEARCH_KEY string = aiSearchAdminKey
output AZURE_STORAGE_ACCOUNT_ID string = storageAccount.id

output BLOB_CONNECTION_STRING string = 'ResourceId=${blobService.id}'
output BLOB_ACCOUNT_URL string = storageAccount.properties.primaryEndpoints.blob
