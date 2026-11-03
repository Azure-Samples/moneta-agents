metadata description = 'Creates a Virtual Network with subnets for Container Apps and Private Endpoints.'

@description('Name of the virtual network')
param name string

@description('Location for the virtual network')
param location string = resourceGroup().location

@description('Tags for the virtual network')
param tags object = {}

@description('Address prefix for the virtual network')
param addressPrefix string = '10.0.0.0/16'

@description('Address prefix for the Container Apps subnet')
param containerAppsSubnetPrefix string = '10.0.0.0/23'

@description('Address prefix for the Private Endpoints subnet')
param privateEndpointsSubnetPrefix string = '10.0.2.0/24'

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: [
      {
        name: 'container-apps-subnet'
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'private-endpoints-subnet'
        properties: {
          addressPrefix: privateEndpointsSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

@description('Resource ID of the virtual network')
output id string = virtualNetwork.id

@description('Name of the virtual network')
output name string = virtualNetwork.name

@description('Resource ID of the Container Apps subnet')
output containerAppsSubnetId string = virtualNetwork.properties.subnets[0].id

@description('Name of the Container Apps subnet')
output containerAppsSubnetName string = virtualNetwork.properties.subnets[0].name

@description('Resource ID of the Private Endpoints subnet')
output privateEndpointsSubnetId string = virtualNetwork.properties.subnets[1].id

@description('Name of the Private Endpoints subnet')
output privateEndpointsSubnetName string = virtualNetwork.properties.subnets[1].name
