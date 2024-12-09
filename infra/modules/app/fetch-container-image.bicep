@description('Set if the container app already exists')
param exists bool

@description('The name of the container app to fetch container information from')
param name string

resource existingApp 'Microsoft.App/containerApps@2023-04-01-preview' existing = if (exists) {
  name: name
}

@description('Array of containers from the existing app or [] if it does not exist')
output containers array = exists ? existingApp.properties.template.containers : []
