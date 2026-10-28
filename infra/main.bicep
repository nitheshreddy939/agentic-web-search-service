targetScope = 'resourceGroup'

@description('Base name for resources')
param name string = 'agentic-web-search'
param location string = resourceGroup().location

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${name}-env'
  location: location
  properties: {}
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: true, targetPort: 8000 }
    }
    template: {
      containers: [
        {
          name: 'api'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // replaced by azd deploy
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'PLANNER', value: 'heuristic' }
            { name: 'LANGSMITH_PROJECT', value: 'agentic-web-search-service' }
          ]
        }
      ]
      scale: { minReplicas: 0, maxReplicas: 3 }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
