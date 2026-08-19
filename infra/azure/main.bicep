targetScope = 'resourceGroup'

@description('Azure region for the ETIS Engineering Studio production foundation.')
param location string = resourceGroup().location

@description('Resource-name prefix.')
param prefix string = 'etis-studio'

@description('Deployment environment name.')
param environment string = 'prod'

@description('PostgreSQL administrator login.')
param postgresAdminUser string = 'etisadmin'

@secure()
@description('PostgreSQL administrator password. Never store this value in source control.')
param postgresAdminPassword string

@description('Application PostgreSQL database name.')
param postgresDbName string = 'etis_studio'

@description('PostgreSQL compute SKU.')
param postgresSkuName string = 'Standard_B1ms'

@description('PostgreSQL compute tier.')
param postgresSkuTier string = 'Burstable'

@minValue(32)
@description('PostgreSQL storage size in GiB.')
param postgresStorageGb int = 32

@minValue(7)
@maxValue(35)
@description('PostgreSQL automatic backup retention in days.')
param postgresBackupRetentionDays int = 7

@description('Log Analytics retention in days.')
param logRetentionDays int = 30

var suffix = uniqueString(subscription().id, resourceGroup().id)
var compactPrefix = toLower(replace(prefix, '-', ''))

var vnetName = '${prefix}-${environment}-vnet'
var containerAppsSubnetName = 'container-apps'
var postgresSubnetName = 'postgres'

var lawName = '${prefix}-${environment}-law'
var appInsightsName = '${prefix}-${environment}-appi'
var acrName = take('${compactPrefix}${environment}${suffix}', 50)
var identityName = '${prefix}-${environment}-runtime'
var keyVaultName = take('${prefix}-${environment}-kv-${suffix}', 24)
var containerAppsEnvironmentName = '${prefix}-${environment}-cae'
var postgresServerName = take('${prefix}-${environment}-pg-${suffix}', 63)

var postgresPrivateDnsZoneName = 'private.postgres.database.azure.com'

var acrPullRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
) // AcrPull

var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
) // Key Vault Secrets User

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.40.0.0/20'
      ]
    }
  }
}

resource containerAppsSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: containerAppsSubnetName
  properties: {
    addressPrefix: '10.40.0.0/23'
    delegations: [
      {
        name: 'container-apps-environment'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}

resource postgresSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: postgresSubnetName
  properties: {
    addressPrefix: '10.40.2.0/24'
    delegations: [
      {
        name: 'postgres-flexible-server'
        properties: {
          serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
        }
      }
    ]
  }
}

resource postgresPrivateDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: postgresPrivateDnsZoneName
  location: 'global'
}

resource postgresPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: postgresPrivateDns
  name: '${prefix}-${environment}-pg-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  properties: {
    retentionInDays: logRetentionDays
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 30
    publicNetworkAccess: 'Enabled'
  }
}

resource runtimeAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, runtimeIdentity.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    roleDefinitionId: acrPullRoleDefinitionId
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource runtimeKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, runtimeIdentity.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: containerAppsEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: listKeys(law.id, law.apiVersion).primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: containerAppsSubnet.id
      internal: false
    }
  }
}

// PostgreSQL is VNet-integrated through the delegated subnet and private DNS.
// No PostgreSQL firewall rule or public application database endpoint is created.
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresServerName
  location: location
  sku: {
    name: postgresSkuName
    tier: postgresSkuTier
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: '16'
    backup: {
      backupRetentionDays: postgresBackupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: postgresSubnet.id
      privateDnsZoneArmResourceId: postgresPrivateDns.id
    }
    storage: {
      storageSizeGB: postgresStorageGb
      autoGrow: 'Enabled'
    }
  }
  dependsOn: [
    postgresPrivateDnsLink
  ]
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: postgresDbName
  properties: {}
}

output containerRegistryName string = acr.name
output containerRegistryLoginServer string = acr.properties.loginServer

output containerAppsEnvironmentName string = containerAppsEnvironment.name
output containerAppsEnvironmentId string = containerAppsEnvironment.id

output runtimeIdentityName string = runtimeIdentity.name
output runtimeIdentityId string = runtimeIdentity.id
output runtimeIdentityClientId string = runtimeIdentity.properties.clientId

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri

output postgresServerName string = postgres.name
output postgresHost string = postgres.properties.fullyQualifiedDomainName
output postgresDatabaseName string = database.name
output postgresAdminUser string = postgresAdminUser

output logAnalyticsWorkspaceName string = law.name
output applicationInsightsName string = appInsights.name
