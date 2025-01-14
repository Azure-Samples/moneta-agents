metadata description = 'Creates an Azure Cognitive Services instance.'

import { roleAssignmentType } from 'br/public:avm/utl/types/avm-common-types:0.4.0'
import { endpointsType, deploymentsType } from 'br/public:avm/res/cognitive-services/account:0.9.1'

param name string
param location string = resourceGroup().location
param tags object = {}

@description('The custom subdomain name used to access the API. Defaults to the value of the name parameter.')
param customSubDomainName string = name

param disableLocalAuth bool = false


@description('Optional. Array of deployments about cognitive service accounts to create.')
param deployments deploymentsType

param kind string = 'OpenAI'

@allowed([ 'Enabled', 'Disabled' ])
param publicNetworkAccess string = 'Enabled'
param sku object = {
  name: 'S0'
}

param allowedIpRules array = []

param networkAcls object = empty(allowedIpRules) ? {
  defaultAction: 'Allow'
} : {
  ipRules: allowedIpRules
  defaultAction: 'Deny'
}

@description('Optional. The Resource ID of the Log Analytics workspace to send diagnostic logs to. If not provided, no logs will be sent.')
param logAnalyticsWorkspaceResourceId string = ''

@description('Optional. The list of role assignments to be created for the cognitive service account.')
param roleAssignments roleAssignmentType[]?

module account 'br/public:avm/res/cognitive-services/account:0.9.1' = {
  name: name
  params: {
    name: name
    kind: kind
    location: location
    tags: tags
    customSubDomainName: customSubDomainName
    publicNetworkAccess: publicNetworkAccess
    networkAcls: networkAcls
    disableLocalAuth: disableLocalAuth
    sku: sku.name
    deployments: deployments
    diagnosticSettings: logAnalyticsWorkspaceResourceId == '' ? [] : [
      {
        name: 'customSetting'
        logCategoriesAndGroups: [
          {
            category: 'RequestResponse'
          }
        {
            category: 'Audit'
          }
        ]
        metricCategories: [
          {
            category: 'AllMetrics'
          }
        ]
        workspaceResourceId: logAnalyticsWorkspaceResourceId
      }
    ]
    roleAssignments: roleAssignments
  }
}

@description('The resource ID of the OpenAI Cognitive Services account.')
output resourceId string = account.outputs.resourceId

@description('The name of the OpenAI Cognitive Services account.')
output name string = account.name

@description('The service endpoint of the cognitive services account.')
output endpoint string = account.outputs.endpoint

@description('All endpoints available for the cognitive services account, types depends on the cognitive service kind.')
output endpoints endpointsType = account.outputs.endpoints

