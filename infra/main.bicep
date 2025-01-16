metadata name = 'moneta'

/* -------------------------------------------------------------------------- */
/*                                 PARAMETERS                                 */
/* -------------------------------------------------------------------------- */

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@description('Principal ID of the user running the deployment')
param azurePrincipalId string

@description('Extra tags to be applied to provisioned resources')
param extraTags object = {}

@description('Location for all resources')
param location string = resourceGroup().location

/* ---------------------------- Shared Resources ---------------------------- */

@maxLength(63)
@description('Name of the log analytics workspace to deploy. If not specified, a name will be generated. The maximum length is 63 characters.')
param logAnalyticsWorkspaceName string = ''

@maxLength(255)
@description('Name of the application insights to deploy. If not specified, a name will be generated. The maximum length is 255 characters.')
param applicationInsightsName string = ''

@description('Application Insights Location')
param appInsightsLocation string = location

@description('The auth tenant id for the frontend and backend app (leave blank in AZD to use your current tenant)')
param authTenantId string = '' // Make sure authTenantId is set if not using AZD

@description('Name of the authentication client secret in the key vault')
param authClientSecretName string = 'AZURE-AUTH-CLIENT-SECRET'

@description('The auth client id for the frontend and backend app')
param authClientId string = ''

@description('Client secret of the authentication client')
@secure()
param authClientSecret string = ''

@maxLength(50)
@description('Name of the container registry to deploy. If not specified, a name will be generated. The name is global and must be unique within Azure. The maximum length is 50 characters.')
param containerRegistryName string = ''

@maxLength(60)
@description('Name of the container apps environment to deploy. If not specified, a name will be generated. The maximum length is 60 characters.')
param containerAppsEnvironmentName string = ''

/* -------------------------------- Frontend -------------------------------- */

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

/* -------------------------------------------------------------------------- */

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
    solution: 'moneta'
  },
  extraTags
)

@description('Azure OpenAI API Version')
var azureOpenAiApiVersion = '2024-12-01-preview'

// Variables for AI Search index names and configurations
var aiSearchCioIndexName = 'cio-index'
var aiSearchFundsIndexName = 'funds-index'
var aiSearchInsIndexName = 'ins-index'

/* --------------------- Globally Unique Resource Names --------------------- */

var _applicationInsightsName = !empty(applicationInsightsName)
  ? applicationInsightsName
  : take('${abbreviations.insightsComponents}${environmentName}', 255)
var _logAnalyticsWorkspaceName = !empty(logAnalyticsWorkspaceName)
  ? logAnalyticsWorkspaceName
  : take('${abbreviations.operationalInsightsWorkspaces}${environmentName}', 63)
var _containerRegistryName = !empty(containerRegistryName)
  ? containerRegistryName
  : take('${abbreviations.containerRegistryRegistries}${take(alphaNumericEnvironmentName, 35)}${resourceToken}', 50)
var _keyVaultName = take('${abbreviations.keyVaultVaults}${alphaNumericEnvironmentName}${resourceToken}', 24)
var _storageAccountName = take(
  '${abbreviations.storageStorageAccounts}${alphaNumericEnvironmentName}${resourceToken}',
  24
)
var _azureOpenAiName = take('${abbreviations.cognitiveServicesOpenAI}${alphaNumericEnvironmentName}', 63)
var _aiHubName = take('${abbreviations.aiPortalHub}${environmentName}', 260)
var _aiProjectName = take('${abbreviations.aiPortalProject}${environmentName}', 260)
var _aiSearchServiceName = take('${abbreviations.searchSearchServices}${environmentName}', 260)
var _containerAppsEnvironmentName = !empty(containerAppsEnvironmentName)
  ? containerAppsEnvironmentName
  : take('${abbreviations.appManagedEnvironments}${environmentName}', 60)

/* ----------------------------- Resource Names ----------------------------- */

var _frontendIdentityName = take(
  '${abbreviations.managedIdentityUserAssignedIdentities}frontend-${environmentName}',
  32
)
var _frontendContainerAppName = !empty(frontendContainerAppName)
  ? frontendContainerAppName
  : take('${abbreviations.appContainerApps}frontend-${environmentName}', 32)
var _backendIdentityName = take('${abbreviations.managedIdentityUserAssignedIdentities}backend-${environmentName}', 32)
var _backendContainerAppName = !empty(backendContainerAppName)
  ? backendContainerAppName
  : take('${abbreviations.appContainerApps}backend-${environmentName}', 32)

/* -------------------------------------------------------------------------- */
/*                                  RESOURCES                                 */
/* -------------------------------------------------------------------------- */

/* -------------------------------- AI Infra  ------------------------------- */

module hub 'modules/ai/hub.bicep' = {
  name: 'hub'
  params: {
    location: location
    tags: tags
    name: _aiHubName
    displayName: _aiHubName
    keyVaultId: keyVault.outputs.resourceId
    storageAccountId: storageAccount.outputs.resourceId
    containerRegistryId: containerRegistry.outputs.resourceId
    applicationInsightsId: appInsightsComponent.outputs.resourceId
    openAiName: azureOpenAi.outputs.name
    openAiConnectionName: 'aoai-connection'
    openAiContentSafetyConnectionName: 'aoai-content-safety-connection'
    aiSearchName: searchService.outputs.name
    aiSearchConnectionName: 'search-service-connection'
  }
}

module project 'modules/ai/project.bicep' = {
  name: 'project'
  params: {
    location: location
    tags: tags
    name: _aiProjectName
    displayName: _aiProjectName
    hubName: hub.outputs.name
  }
}

module storageAccount 'br/public:avm/res/storage/storage-account:0.15.0' = {
  name: 'storageAccount'
  scope: resourceGroup()
  params: {
    location: location
    tags: tags
    name: _storageAccountName
    kind: 'StorageV2'
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
        {
          name: 'default'
          publicAccess: 'None'
        }
      ]
      // corsRules: [
      //   {
      //     allowedOrigins: [
      //       'https://mlworkspace.azure.ai'
      //       'https://ml.azure.com'
      //       'https://*.ml.azure.com'
      //       'https://ai.azure.com'
      //       'https://*.ai.azure.com'
      //       'https://mlworkspacecanary.azure.ai'
      //       'https://mlworkspace.azureml-test.net'
      //     ]
      //     allowedMethods: [
      //       'GET'
      //       'HEAD'
      //       'POST'
      //       'PUT'
      //       'DELETE'
      //       'OPTIONS'
      //       'PATCH'
      //     ]
      //     maxAgeInSeconds: 1800
      //     exposedHeaders: [
      //       '*'
      //     ]
      //     allowedHeaders: [
      //       '*'
      //     ]
      //   }
      // ]
     deleteRetentionPolicy: {
        allowPermanentDelete: false
        enabled: false
      }
      shareDeleteRetentionPolicy: {
        enabled: true
        days: 7
      }
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
            {
              roleDefinitionIdOrName: 'Storage Blob Data Contributor'
              principalId: backendIdentity.outputs.principalId
              principalType: 'ServicePrincipal'
            }
      ]
  }
}

// Also rerefernced in the outputs with the sequential index
// order of the model definitions is important
param embedModel string = 'text-embedding-3-large'
var deployments = [
     {
        name: 'gpt-4o-2024-08-06'
        sku: {
          name: 'GlobalStandard'
          capacity: 50
        }
        model: {
          format: 'OpenAI'
          name: 'gpt-4o'
          version: '2024-08-06'
        }
        versionUpgradeOption: 'OnceCurrentVersionExpired'
      }
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
    ]

module azureOpenAi 'modules/ai/cognitiveservices.bicep' = {
  name: 'cognitiveServices'
  params: {
    location: location
    tags: tags
    name: _azureOpenAiName
    kind: 'AIServices'
    customSubDomainName: _azureOpenAiName
    deployments:  deployments
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Cognitive Services OpenAI User'
        principalId: backendIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
      }
      {
        roleDefinitionIdOrName: 'Cognitive Services OpenAI Contributor'
        principalId: azurePrincipalId
      }
    ]
  }
}

// TEMP SOLUTION : Used for data load only.
// TODO: switch the data load script to the SDK that supports cognitive services domain
var embeddingDeployments = [
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
    ]

module openAiEmbeddings 'br/public:avm/res/cognitive-services/account:0.8.0' = {
  name: 'openai-dataload-embeddings'
  scope: resourceGroup()
  params: {
    name: 'oai-load-${resourceToken}'
    location: location
    kind: 'OpenAI'
    customSubDomainName: 'oai-load-${resourceToken}'
    sku: 'S0'
    deployments: embeddingDeployments
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {}
    roleAssignments: [
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

module searchService 'br/public:avm/res/search/search-service:0.8.2' = {
  name: _aiSearchServiceName
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

resource searchIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'aiSearchService'
  location: location
}

/* ---------------------------- Observability  ------------------------------ */

module logAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.9.1' = {
  name: 'workspaceDeployment'
  params: {
    name: _logAnalyticsWorkspaceName
    location: location
    tags: tags
    dataRetention: 30
  }
}

module appInsightsComponent 'br/public:avm/res/insights/component:0.4.2' = {
  name: _applicationInsightsName
  params: {
    name: _applicationInsightsName
    location: appInsightsLocation
    workspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
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



/* ------------------------ Common App Resources  -------------------------- */

module containerRegistry 'modules/app/container-registry.bicep' = {
  name: _containerRegistryName
  scope: resourceGroup()
  params: {
    location: location
    pullingIdentityNames: [
      _frontendIdentityName
      _backendIdentityName
    ]
    tags: tags
    name: '${abbreviations.containerRegistryRegistries}${resourceToken}'
  }
}

module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.8.1' = {
  name: 'containerAppsEnvironment'
  params: {
    name: _containerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceResourceId: logAnalyticsWorkspace.outputs.resourceId
    daprAIConnectionString: appInsightsComponent.outputs.connectionString
    zoneRedundant: false
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
    enablePurgeProtection: false // Set to true to if you deploy in production and want to protect against accidental deletion
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Key Vault Secrets User'
        principalId: frontendIdentity.outputs.principalId
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
    secrets: empty(authClientSecret)
      ? []
      : [
          {
            name: authClientSecretName
            value: authClientSecret
          }
        ]
  }
}

/* ------------------------------ Frontend App ------------------------------ */

module frontendIdentity './modules/app/identity.bicep' = {
  name: 'frontendIdentity'
  scope: resourceGroup()
  params: {
    location: location
    identityName: _frontendIdentityName
  }
}

var keyvaultIdentities = authClientSecret != ''
  ? {
      'microsoft-provider-authentication-secret': {
        keyVaultUrl: '${keyVault.outputs.uri}secrets/${authClientSecretName}'
        identity: frontendIdentity.outputs.resourceId
      }
    }
  : {}

module frontendApp 'modules/app/container-apps.bicep' = {
  name: 'frontend-container-app'
  scope: resourceGroup()
  params: {
    name: _frontendContainerAppName
    tags: tags
    identityId: frontendIdentity.outputs.resourceId
    containerAppsEnvironmentName: containerAppsEnvironment.outputs.name
    containerRegistryName: containerRegistry.outputs.name
    exists: frontendExists
    serviceName: 'frontend' // Must match the service name in azure.yaml
    env: {
      // BACKEND_ENDPOINT: backendApp.outputs.URL
      BACKEND_ENDPOINT: backendApp.outputs.URL

      // Required for the frontend app to ask for a token for the backend app
      AZURE_CLIENT_APP_ID: authClientId

      // Required for container app daprAI
      APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsComponent.outputs.connectionString

      // Required for managed identity
      AZURE_CLIENT_ID: frontendIdentity.outputs.clientId
      
    }
    keyvaultIdentities: keyvaultIdentities
  }
}

module frontendContainerAppAuth 'modules/app/container-apps-auth.bicep' = if (authClientSecret != '') {
  name: 'frontend-container-app-auth-module'
  params: {
    name: frontendApp.outputs.name
    clientId: authClientId
    clientSecretName: 'microsoft-provider-authentication-secret'
    openIdIssuer: '${environment().authentication.loginEndpoint}${authTenantId}/v2.0' // Works only for Microsoft Entra
    unauthenticatedClientAction: 'RedirectToLoginPage'
    allowedApplications: [
      '04b07795-8ddb-461a-bbee-02f9e1bf7b46' // AZ CLI for testing purposes
    ]
  }
}

/* ------------------------------ Backend App ------------------------------- */

module backendIdentity './modules/app/identity.bicep' = {
  name: 'backendIdentity'
  scope: resourceGroup()
  params: {
    location: location
    identityName: _backendIdentityName
  }
}

module backendApp 'modules/app/container-apps.bicep' = {
  name: 'backend-container-app'
  scope: resourceGroup()
  params: {
    name: _backendContainerAppName
    tags: tags
    identityId: backendIdentity.outputs.resourceId
    containerAppsEnvironmentName: containerAppsEnvironment.outputs.name
    containerRegistryName: containerRegistry.outputs.name
    exists: backendExists
    serviceName: 'backend' // Must match the service name in azure.yaml
    externalIngressAllowed: false // Set to true if you intend to call backend from the locallly deployed frontend
    // Setting to true will allow traffic from anywhere
    env: {
      // Required for container app daprAI
      APPLICATIONINSIGHTS_CONNECTION_STRING: appInsightsComponent.outputs.connectionString
      AZURE_RESOURCE_GROUP: resourceGroup().name
      SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS: true
      SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS_SENSITIVE: true // OBS! You might want to remove this in production

      // Required for managed identity
      AZURE_CLIENT_ID: backendIdentity.outputs.clientId
      AZURE_OPENAI_ENDPOINT: azureOpenAi.outputs.endpoint
      AZURE_OPENAI_DEPLOYMENT_NAME: deployments[0].name
      AZURE_OPENAI_API_VERSION: azureOpenAiApiVersion

      // OLD TO BE MIGRATED
      AI_SEARCH_CIO_INDEX_NAME: aiSearchCioIndexName
      AI_SEARCH_ENDPOINT: 'https://${searchService.outputs.name}.search.windows.net'
      AI_SEARCH_FUNDS_INDEX_NAME: aiSearchFundsIndexName
      AI_SEARCH_INS_INDEX_NAME: aiSearchInsIndexName

      COSMOSDB_CONTAINER_CLIENT_NAME: cosmosDbCRMContainerName
      COSMOSDB_CONTAINER_FSI_BANK_USER_NAME: cosmosDbBankingContainerName
      COSMOSDB_CONTAINER_FSI_INS_USER_NAME: cosmosDbInsuranceContainerName
      COSMOSDB_DATABASE_NAME: cosmosDbDatabaseName
      COSMOSDB_ENDPOINT: cosmosDbAccount.properties.documentEndpoint

      HANDLER_TYPE: 'semantickernel'

    }
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
/*                                   OUTPUTS                                  */
/* -------------------------------------------------------------------------- */

// Outputs are automatically saved in the local azd environment .env file.
// To see these outputs, run `azd env get-values`,  or
// `azd env get-values --output json` for json output.
// To generate your own `.env` file run `azd env get-values > .env`

@description('The endpoint of the container registry.') // necessary for azd deploy
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer

@description('Endpoint URL of the Frontend service')
output SERVICE_FRONTEND_URL string = frontendApp.outputs.URL

@description('Endpoint URL of the Backend service')
output SERVICE_BACKEND_URL string = backendApp.outputs.URL

@description('ID of the tenant we are deploying to')
output AZURE_AUTH_TENANT_ID string = authTenantId

@description('Principal ID of the user running the deployment')
output AZURE_PRINCIPAL_ID string = azurePrincipalId

@description('Application registration client ID')
output AZURE_CLIENT_APP_ID string = authClientId

@description('Azure OpenAI name')
output AZURE_OPENAI_NAME string = azureOpenAi.outputs.name

@description('Azure OpenAI endpoint')
output AZURE_OPENAI_ENDPOINT string = azureOpenAi.outputs.endpoint

@description('Azure OpenAI Core Model Deployment Name')
output AZURE_OPENAI_DEPLOYMENT_NAME string = deployments[0].name

@description('Azure OpenAI Core Model Deployment Name')
output AZURE_OPENAI_API_VERSION string = azureOpenAiApiVersion

@description('Application Insights name')
output AZURE_APPLICATION_INSIGHTS_NAME string = appInsightsComponent.outputs.name

@description('Log Analytics Workspace name')
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = logAnalyticsWorkspace.outputs.name

@description('Application Insights connection string')
output APPLICATIONINSIGHTS_CONNECTION_STRING string = appInsightsComponent.outputs.connectionString

output COSMOSDB_ACCOUNT_NAME string = cosmosDbAccountName
output COSMOSDB_ENDPOINT string = cosmosDbAccount.properties.documentEndpoint
output COSMOSDB_DATABASE_NAME string = cosmosDbDatabaseName

output COSMOSDB_CONTAINER_CLIENT_NAME string = cosmosDbCRMContainerName
output COSMOSDB_CONTAINER_FSI_BANK_USER_NAME string = cosmosDbBankingContainerName
output COSMOSDB_CONTAINER_FSI_INS_USER_NAME string = cosmosDbInsuranceContainerName

output AI_SEARCH_ENDPOINT string = 'https://${searchService.outputs.name}.search.windows.net'
output AI_SEARCH_PRINCIPAL_ID string = searchIdentity.properties.principalId
output AI_SEARCH_IDENTITY_ID string = searchIdentity.id

output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = embeddingDeployments[0].name
output AZURE_OPENAI_EMBEDDING_MODEL string = embeddingDeployments[0].model.name
output AZURE_OPENAI_EMBEDDING_ENDPOINT string = openAiEmbeddings.outputs.endpoint

// Must match the index names created automatically by postdeploy
output AI_SEARCH_CIO_INDEX_NAME string = aiSearchCioIndexName
output AI_SEARCH_FUNDS_INDEX_NAME string = aiSearchFundsIndexName
output AI_SEARCH_INS_INDEX_NAME string = aiSearchInsIndexName

output AZURE_STORAGE_ACCOUNT_ID string = storageAccount.outputs.resourceId
output AZURE_STORAGE_ACCOUNT_ENDPOINT string = storageAccount.outputs.primaryBlobEndpoint

@description('Semantic Kernel Diagnostics')
output SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS bool = true
output SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS_SENSITIVE bool = true
