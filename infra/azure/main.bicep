targetScope = 'resourceGroup'

@description('Deployment region')
param location string = resourceGroup().location
param prefix string = 'etis-studio'
param environment string = 'prod'
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
@secure()
param postgresAdminPassword string
param postgresAdminUser string = 'etisadmin'
param postgresDbName string = 'etis_studio'

var suffix = uniqueString(resourceGroup().id)
var acrName = replace('${prefix}${environment}${suffix}', '-', '')
var lawName = '${prefix}-${environment}-law'
var caeName = '${prefix}-${environment}-cae'
var appName = '${prefix}-${environment}'
var pgName = '${prefix}-${environment}-pg-${suffix}'
var kvName = take(replace('${prefix}-${environment}-kv-${suffix}', '_','-'),24)

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  properties: { retentionInDays: 30 }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: caeName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: listKeys(law.id, law.apiVersion).primarySharedKey
      }
    }
  }
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A' name: 'standard' }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 30
    publicNetworkAccess: 'Enabled'
  }
}

resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: pgName
  location: location
  sku: { name: 'Standard_B1ms' tier: 'Burstable' }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7 geoRedundantBackup: 'Disabled' }
  }
}

resource db 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: pg
  name: postgresDbName
  properties: {}
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: true targetPort: 8000 transport: 'auto' allowInsecure: false }
      registries: []
    }
    template: {
      containers: [
        {
          name: 'studio'
          image: containerImage
          env: [
            { name: 'ETIS_ENV' value: environment }
            { name: 'ETIS_DEV_LOGIN' value: 'false' }
            { name: 'ETIS_COURSE_NAMESPACE' value: 'COMP330-F26' }
          ]
          resources: { cpu: json('0.5') memory: '1Gi' }
        }
      ]
      scale: { minReplicas: 0 maxReplicas: 5 rules: [{ name: 'http' http: { metadata: { concurrentRequests: '25' } } }] }
    }
  }
}

output containerRegistry string = acr.properties.loginServer
output containerAppName string = app.name
output containerAppFqdn string = app.properties.configuration.ingress.fqdn
output postgresHost string = pg.properties.fullyQualifiedDomainName
output keyVaultName string = kv.name
