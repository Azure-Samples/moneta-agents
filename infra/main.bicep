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

@description('The auth client id for the frontend and backend app')
param authClientId string = ''

@description('The auth tenant id for the frontend and backend app (leave blank in AZD to use your current tenant)')
param authTenantId string = '' // Make sure authTenantId is set if not using AZD

/* ---------------------------- Shared Resources ---------------------------- */

@maxLength(50)
@description('Name of the container registry to deploy. If not specified, a name will be generated. The name is global and must be unique within Azure. The maximum length is 50 characters.')
param containerRegistryName string = ''

@maxLength(60)
@description('Name of the container apps environment to deploy. If not specified, a name will be generated. The maximum length is 60 characters.')
param containerAppsEnvironmentName string = ''

/* --------------------------------- Backend -------------------------------- */

@maxLength(32)
@description('Name of the frontend container app to deploy. If not specified, a name will be generated. The maximum length is 32 characters.')
param frontendContainerAppName string = ''

@description('Set if the frontend container app already exists.')
param frontendExists bool = false

/* --------------------------------- Backend -------------------------------- */

@maxLength(32)
@description('Name of the backend container app to deploy. If not specified, a name will be generated. The maximum length is 32 characters.')
param backendContainerAppName string = ''

@description('Set if the backend container app already exists.')
param backendExists bool = false

@description('Name of the authentication client secret in the key vault')
param authClientSecretName string = 'AZURE-AUTH-CLIENT-SECRET'

@description('Client secret of the authentication client')
@secure()
param authClientSecret string = ''

@maxLength(255)
@description('Name of the application insights to deploy. If not specified, a name will be generated. The maximum length is 255 characters.')
param applicationInsightsName string = ''

/* -------------------------------------------------------------------------- */

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

@description('Application Insights Location')
param appInsightsLocation string = location

/* -------------------------------------------------------------------------- */
/*                                  VARIABLES                                 */
/* -------------------------------------------------------------------------- */

// Load abbreviations from JSON file
var abbreviations = loadJsonContent('./abbreviations.json')

@description('Generate a unique token to make global resource names unique')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

@description('Name of the environment with only alphanumeric characters. Used for resource names that require alphanumeric characters only')
var alphaNumericEnvironmentName = replace(replace(environmentName, '-', ''), ' ', '')

@description('Tags to be applied to all provisioned resources')
var tags = union(
  {
    'azd-env-name': environmentName
    solution: 'moneta-agentic-gbb-ai-1.0'
  },
  extraTags
)


/* --------------------- Globally Unique Resource Names --------------------- */

var _containerRegistryName = !empty(containerRegistryName)
  ? containerRegistryName
  : take('${abbreviations.containerRegistryRegistries}${take(alphaNumericEnvironmentName, 35)}${resourceToken}', 50)

/* ----------------------------- Resource Names ----------------------------- */

var _frontendContainerAppName = !empty(frontendContainerAppName)
  ? frontendContainerAppName
  : take('${abbreviations.appContainerApps}frontend-${environmentName}', 32)
var _backendContainerAppName = !empty(backendContainerAppName)
  ? backendContainerAppName
  : take('${abbreviations.appContainerApps}backend-${environmentName}', 32)
var _containerAppsEnvironmentName = !empty(containerAppsEnvironmentName)
  ? containerAppsEnvironmentName
  : take('${abbreviations.appManagedEnvironments}${environmentName}', 60)
var _appIdentityName = take('${abbreviations.managedIdentityUserAssignedIdentities}${environmentName}', 32)
var _keyVaultName = take('${abbreviations.keyVaultVaults}${alphaNumericEnvironmentName}${resourceToken}', 24)
var _applicationInsightsName = !empty(applicationInsightsName) ? applicationInsightsName : take('${abbreviations.insightsComponents}${environmentName}', 255)


/* -------------------------------------------------------------------------- */

// Variables for AI Search index names and configurations
var aiSearchCioIndexName = 'cio-index'
var aiSearchCioSemanticConfiguration = 'default'
var aiSearchFundsIndexName = 'funds-index'
var aiSearchFundsSemanticConfiguration = 'default'
var aiSearchInsIndexName = 'ins-index'
var aiSearchInsSemanticConfiguration = 'default'
// var aiSearchVectorFieldName = 'contentVector'

// Define common tags  

/* -------------------------------------------------------------------------- */
// [ IDENTITIES ] 
module appIdentity './modules/app/identity.bicep' = {
  name: 'appIdentity'
  scope: resourceGroup()
  params: {
    location: location
    identityName: _appIdentityName
  }
}

module backendIdentity './modules/app/identity-backend.bicep' = {
  name: 'backendIdentity'
  scope: resourceGroup()
  params: {
    location: location
    identityName: 'backend-${_appIdentityName}'
  }
}

resource searchIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'aiSearchService'
  location: location
}

/* -------------------------------------------------------------------------- */
/*                                  RESOURCES                                 */
/* -------------------------------------------------------------------------- */


// ------------------------
// [ Array of OpenAI Model deployments ]
param aoaiGpt4ModelName string = 'gpt-4o'
param aoaiGpt4ModelVersion string = '2024-05-13'
param azureOpenaiApiVersion string = '2024-08-01-preview'
param embedModel string = 'text-embedding-3-large'

var deployments = [
  {
    name: embedModel
    model: {
      format: 'OpenAI'
      name: embedModel
      version: '1'
    }
    sku: { 
      name: 'Standard' 
      capacity: 50 }
  }
  {
    name: '${aoaiGpt4ModelName}-${aoaiGpt4ModelVersion}'
    model: {
      format: 'OpenAI'
      name: aoaiGpt4ModelName
      version: aoaiGpt4ModelVersion
    }
    sku: { 
      name: 'GlobalStandard'
      capacity:  30
    }
  }]

module openAi 'br/public:avm/res/cognitive-services/account:0.8.0' = {
  name: 'openai'
  scope: resourceGroup()
  params: {
    name: 'oai-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'aoai-${tags['azd-env-name']}' })
    kind: 'OpenAI'
    customSubDomainName: 'oai-${resourceToken}'
    sku: 'S0'
    deployments: deployments
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {}
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
        principalId: backendIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
        principalId: searchIdentity.properties.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
        principalId: azurePrincipalId
        principalType: 'User'
      }
    ]
  }
}

module containerRegistry 'modules/app/registry.bicep' = {
  name: 'registry'
  scope: resourceGroup()
  params: {
    location: location
    identityName: appIdentity.outputs.name
    backendIdentityName: backendIdentity.outputs.name
    tags: tags
    name: '${abbreviations.containerRegistryRegistries}${resourceToken}'
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: _containerAppsEnvironmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    daprAIConnectionString: appInsights.properties.ConnectionString
  }
}

module keyVault 'br/public:avm/res/key-vault/vault:0.11.0' = {
  name: 'keyVault'
  scope: resourceGroup()
  params: {
    location: location
    tags: tags
    name: _keyVaultName
    enableRbacAuthorization: true
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Key Vault Secrets User'
        principalId: appIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Key Vault Secrets User'
        principalId: backendIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        principalId: azurePrincipalId
        roleDefinitionIdOrName: 'Key Vault Administrator'
      }
    ]
    secrets: [
      {
        name: authClientSecretName
        value: authClientSecret
      }
    ]
  }
}

/* ------------------------------ Frontend App ------------------------------ */

module frontendApp 'modules/app/containerapp.bicep' = {
  name: 'frontend-container-app'
  scope: resourceGroup()
  params: {
    name: _frontendContainerAppName
    tags: tags
    identityId: appIdentity.outputs.identityId
    containerAppsEnvironmentName: containerAppsEnvironment.name
    containerRegistryName: containerRegistry.outputs.name
    exists: frontendExists
    serviceName: 'frontend' // Must match the service name in azure.yaml
    env: {
      // TODO: remove this when the auth has been removed from the frontend app
      DISABLE_LOGIN: 'True'

      // BACKEND_ENDPOINT: backendApp.outputs.URL
      BACKEND_ENDPOINT: backendApp.outputs.internalUrl

      // required for container app daprAI
      APPLICATIONINSIGHTS_CONNECTION_STRING: appInsights.properties.ConnectionString

      AZURE_CLIENT_ID: appIdentity.outputs.clientId
    }
    keyvaultIdentities: {
      'microsoft-provider-authentication-secret': {
        keyVaultUrl: '${keyVault.outputs.uri}secrets/${authClientSecretName}'
        identity: appIdentity.outputs.identityId
      }
    }
  }
}

module frontendContainerAppAuth 'modules/app/container-apps-auth.bicep' = {
  name: 'frontend-container-app-auth-module'
  params: {
    name: frontendApp.outputs.name
    clientId: authClientId
    clientSecretName: 'microsoft-provider-authentication-secret'
    openIdIssuer: '${environment().authentication.loginEndpoint}${authTenantId}/v2.0' // Works only for Microsoft Entra
    unauthenticatedClientAction: 'RedirectToLoginPage'
    allowedApplications:[
      authClientId
      '04b07795-8ddb-461a-bbee-02f9e1bf7b46' // AZ CLI for testing purposes
    ]
  }
}

/* ------------------------------ Backend App ------------------------------- */

module backendApp 'modules/app/containerapp.bicep' = {
  name: 'backend-container-app'
  scope: resourceGroup()
  params: {
    name: _backendContainerAppName
    tags: tags
    identityId: backendIdentity.outputs.identityId 
    containerAppsEnvironmentName: containerAppsEnvironment.name
    containerRegistryName: containerRegistry.outputs.name
    exists: backendExists
    serviceName: 'backend' // Must match the service name in azure.yaml
    externalIngressAllowed: false
    env: {
      AI_SEARCH_CIO_INDEX_NAME: aiSearchCioIndexName
      AI_SEARCH_ENDPOINT: 'https://${searchService.outputs.name}.search.windows.net'
      AI_SEARCH_FUNDS_INDEX_NAME: aiSearchFundsIndexName
      AI_SEARCH_INS_INDEX_NAME: aiSearchInsIndexName
      AI_SEARCH_INS_SEMANTIC_CONFIGURATION: aiSearchInsSemanticConfiguration
      AZURE_OPENAI_API_VERSION: azureOpenaiApiVersion
      AZURE_OPENAI_DEPLOYMENT_NAME: deployments[1].name
      AZURE_OPENAI_ENDPOINT: openAi.outputs.endpoint
      COSMOSDB_CONTAINER_CLIENT_NAME: cosmosDbCRMContainerName
      COSMOSDB_CONTAINER_FSI_BANK_USER_NAME: cosmosDbBankingContainerName
      COSMOSDB_CONTAINER_FSI_INS_USER_NAME: cosmosDbInsuranceContainerName
      COSMOSDB_DATABASE_NAME: cosmosDbDatabaseName
      COSMOSDB_ENDPOINT: cosmosDbAccount.properties.documentEndpoint
      HANDLER_TYPE: 'semantickernel'

      // required for container app daprAI
      APPLICATIONINSIGHTS_CONNECTION_STRING: appInsights.properties.ConnectionString

      // required for managed identity
      AZURE_CLIENT_ID: backendIdentity.outputs.clientId
    }
    keyvaultIdentities: {
      'microsoft-provider-authentication-secret': {
        keyVaultUrl: '${keyVault.outputs.uri}secrets/${authClientSecretName}'
        identity: backendIdentity.outputs.identityId
      }
    }
  }
}

// module backendContainerAppAuth 'modules/app/container-apps-auth.bicep' = {
//   name: 'backend-container-app-auth-module'
//   params: {
//     name: backendApp.outputs.name
//     clientId: authClientId
//     clientSecretName: 'microsoft-provider-authentication-secret'
//     openIdIssuer: '${environment().authentication.loginEndpoint}${authTenantId}/v2.0' // Works only for Microsoft Entra
//     unauthenticatedClientAction: 'Return401'
//     allowedApplications:[
//       authClientId
//       '04b07795-8ddb-461a-bbee-02f9e1bf7b46' // AZ CLI for testing purposes
//     ]
//   }
// }

// Cosmos DB Role Assignments
resource cosmosDbRoleDefinition 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: cosmosDbAccount
  name: 'b24988ac-6180-42a0-ab88-20f7382dd24c' // Built-in role: Cosmos DB Account Reader Role
}

resource cosmosDbRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(cosmosDbAccount.id, _backendContainerAppName, cosmosDbRoleDefinition.id)
  scope: cosmosDbAccount
  properties: {
    principalId: backendIdentity.outputs.principalId
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
    principalId: backendIdentity.outputs.principalId
    scope: cosmosDbAccount.id
  }
}

resource cosmosDbDataContributorRoleAssignmentPrincipal 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2021-04-15' = {
  parent: cosmosDbAccount
  name: guid(cosmosDbAccount.id, azurePrincipalId, cosmosDbDataContributorRoleDefinition.id)
  properties: {
    roleDefinitionId: cosmosDbDataContributorRoleDefinition.id
    principalId: azurePrincipalId
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
  name: _applicationInsightsName
  location: appInsightsLocation
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

/* -------------------------------------------------------------------------- */
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

/* -------------------------------------------------------------------------- */
// Storage Account
module storage 'br/public:avm/res/storage/storage-account:0.9.1' = {
  name: storageAccountName
  scope: resourceGroup()
  params: {
    name: storageAccountName
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    publicNetworkAccess: 'Enabled' // Necessary for uploading documents to storage container
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    blobServices: {
      deleteRetentionPolicyDays: 2
      deleteRetentionPolicyEnabled: true
      containers: [
        {
          name: aiSearchInsIndexName
          publicAccess: 'None'
        }
        {
          name: aiSearchCioIndexName
          publicAccess: 'None'
        }
        {
          name: aiSearchFundsIndexName
          publicAccess: 'None'
        }
      ]
    }
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalId: searchIdentity.properties.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
        principalId: azurePrincipalId
        principalType: 'User'
      }
    ]
  }
}

/* -------------------------------------------------------------------------- */
// AI Search Service (Azure Cognitive Search)

module searchService 'br/public:avm/res/search/search-service:0.7.1' = {
  name: 'search-service'
  scope: resourceGroup()
  params: {
    name: toLower('search${uniqueString(resourceGroup().id)}')
    location: location
    tags: tags
    // disableLocalAuth: true
    // semanticSearch: 'standard'
    sku: 'basic'
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    managedIdentities: { userAssignedResourceIds: [searchIdentity.id] }
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Search Index Data Contributor'
        principalId: backendIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Search Service Contributor'
        principalId: backendIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Search Index Data Contributor'
        principalId: azurePrincipalId
        principalType: 'User'
      }
      {
        roleDefinitionIdOrName: 'Search Service Contributor'
        principalId: azurePrincipalId
        principalType: 'User'
      }
    ]
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

@description('Endpoint URL of string Frontend service') // reused by identity management scripts
output SERVICE_FRONTEND_URL string = frontendApp.outputs.URL

@description('Endpoint URL of the Backend service') // reused by identity management scripts
output SERVICE_BACKEND_URL string = backendApp.outputs.URL

/* -------------------------------------------------------------------------- */

output COSMOSDB_ACCOUNT_NAME string = cosmosDbAccountName

output COSMOSDB_ENDPOINT string = cosmosDbAccount.properties.documentEndpoint
output COSMOSDB_DATABASE_NAME string = cosmosDbDatabaseName

output COSMOSDB_CONTAINER_CLIENT_NAME string = cosmosDbCRMContainerName
output COSMOSDB_CONTAINER_FSI_BANK_USER_NAME string = cosmosDbBankingContainerName
output COSMOSDB_CONTAINER_FSI_INS_USER_NAME string = cosmosDbInsuranceContainerName

output AI_SEARCH_ENDPOINT string = 'https://${searchService.outputs.name}.search.windows.net'
output AI_SEARCH_PRINCIPAL_ID string = searchIdentity.properties.principalId
output AI_SEARCH_IDENTITY_ID string = searchIdentity.id

output AZURE_OPENAI_API_VERSION string = azureOpenaiApiVersion
output AZURE_OPENAI_DEPLOYMENT_NAME string = deployments[1].name
output AZURE_OPENAI_ENDPOINT string = openAi.outputs.endpoint
output AZURE_PRINCIPAL_ID string = azurePrincipalId
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = deployments[0].name
output AZURE_OPENAI_EMBEDDING_MODEL string = deployments[0].model.name

output AI_SEARCH_CIO_INDEX_NAME string = 'moneta-cio-vector'
output AI_SEARCH_FUNDS_INDEX_NAME string = 'moneta-funds-vector'
output AI_SEARCH_FUNDS_SEMANTIC_CONFIGURATION string = 'default'

output AI_SEARCH_INS_INDEX_NAME string = aiSearchInsIndexName
output AI_SEARCH_INS_SEMANTIC_CONFIGURATION string = aiSearchInsSemanticConfiguration

output AZURE_STORAGE_ACCOUNT_ID string = storage.outputs.resourceId
output AZURE_STORAGE_ACCOUNT_ENDPOINT string = storage.outputs.primaryBlobEndpoint
