metadata description = 'Creates an Azure Container Apps Auth Config using Microsoft Entra as Identity Provider'

@description('The name of the container apps resource within the current resource group scope')
param name string

@description('The client ID of the Microsoft Entra application')
param clientId string

@description('The name of the Container Apps secret that contains the client secret of the Microsoft Entra application')
param clientSecretName string

@description('The OpenID issuer of the Microsoft Entra application')
param openIdIssuer string

@description('App IDs of the applications that are allowed to access the app')
param allowedApplications array = []

@description('App URIs of the allowed audiences')
param allowedAudiences array = []


@description('The action to take when an unauthenticated client accesses the app')
@allowed([
  'RedirectToLoginPage'
  'AllowAnonymous'
  'Return401'
  'Return403'
])
param unauthenticatedClientAction string = 'RedirectToLoginPage'

resource app 'Microsoft.App/containerApps@2023-05-01' existing = {
  name: name
}

resource auth 'Microsoft.App/containerApps/authConfigs@2024-03-01' = {
  parent: app
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      redirectToProvider: 'azureactivedirectory'
      unauthenticatedClientAction: unauthenticatedClientAction
    }
    identityProviders: {
      azureActiveDirectory: {
        registration: {
          clientId: clientId
          clientSecretSettingName: clientSecretName
          openIdIssuer: openIdIssuer
        }
        validation: {
          defaultAuthorizationPolicy: {
            allowedApplications: allowedApplications
          }
          allowedAudiences: allowedAudiences
        }
      }
    }
  }
}
