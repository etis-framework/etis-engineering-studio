targetScope = 'resourceGroup'

@description('Azure region for the ETIS Engineering Studio migration job.')
param location string = resourceGroup().location

@description('Resource-name prefix. Must match the foundation deployment.')
param prefix string = 'etis-studio'

@description('Deployment environment name. Must match the foundation deployment.')
param environment string = 'prod'

@description('Immutable production image to run, normally the ACR image tagged with the validated Git commit SHA.')
param containerImage string

@description('Key Vault secret containing the PostgreSQL SQLAlchemy connection URL.')
param databaseUrlSecretName string = 'etis-database-url'

var suffix = uniqueString(subscription().id, resourceGroup().id)
var compactPrefix = toLower(replace(prefix, '-', ''))

var acrName = take('${compactPrefix}${environment}${suffix}', 50)
var runtimeIdentityName = '${prefix}-${environment}-runtime'
var keyVaultName = take('${prefix}-${environment}-kv-${suffix}', 24)
var containerAppsEnvironmentName = '${prefix}-${environment}-cae'
var migrationJobName = '${prefix}-${environment}-migrate'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: runtimeIdentityName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' existing = {
  name: containerAppsEnvironmentName
}

// Migrations execute from inside the Container Apps environment so the job can
// reach the private VNet-integrated PostgreSQL Flexible Server. GitHub-hosted
// runners never require direct network access to the production database.
resource migrationJob 'Microsoft.App/jobs@2025-07-01' = {
  name: migrationJobName
  location: location

  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentity.id}': {}
    }
  }

  properties: {
    environmentId: containerAppsEnvironment.id

    configuration: {
      triggerType: 'Manual'

      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }

      replicaRetryLimit: 1
      replicaTimeout: 600

      registries: [
        {
          server: acr.properties.loginServer
          identity: runtimeIdentity.id
        }
      ]

      secrets: [
        {
          name: 'database-url'
          identity: runtimeIdentity.id
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${databaseUrlSecretName}'
        }
      ]
    }

    template: {
      containers: [
        {
          name: 'migration'
          image: containerImage

          command: [
            'alembic'
          ]

          args: [
            'upgrade'
            'head'
          ]

          env: [
            {
              name: 'ETIS_DATABASE_URL'
              secretRef: 'database-url'
            }
          ]

          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

output migrationJobName string = migrationJob.name
