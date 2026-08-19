targetScope = 'resourceGroup'

@description('Azure region for the ETIS Engineering Studio application.')
param location string = resourceGroup().location

@description('Resource-name prefix. Must match the foundation deployment.')
param prefix string = 'etis-studio'

@description('Deployment environment name. Must match the foundation deployment.')
param environment string = 'prod'

@description('Immutable production image, normally tagged with the validated Git commit SHA.')
param containerImage string

@description('Canonical HTTPS origin for the Engineering Studio.')
param webOrigin string

@description('Canonical custom hostname bound to the production Container App.')
param customDomainName string

@description('Existing managed certificate name for the canonical custom hostname.')
param managedCertificateName string

@description('Course namespace exposed by this production deployment.')
param courseNamespace string = 'COMP330-F26'

@description('Primary instructor GitHub login.')
param instructorGithub string = 'woconnell1'

@description('Microsoft Entra application client ID.')
param entraClientId string

@description('Microsoft Entra tenant UUID.')
param entraTenant string

@description('Microsoft Entra OAuth redirect URI.')
param entraRedirectUri string

@description('Allowed institutional Entra email domain.')
param entraAllowedDomain string = 'luc.edu'

@description('Exact Microsoft Entra Object ID for the designated production-acceptance test student.')
param productionTestStudentOid string

@description('Canonical email for the designated production-acceptance test student.')
param productionTestStudentEmail string

@description('Studio student ID for the designated production-acceptance test student.')
param productionTestStudentId string = 'production-test-student'

@description('Section key reserved for production-acceptance student testing.')
param productionTestSectionKey string = 'PRODUCTION-TEST'

@description('Team key reserved for production-acceptance student testing.')
param productionTestTeamKey string = 'production-test-team'

@description('GitHub App ID.')
param githubAppId string

@description('GitHub App slug.')
param githubAppSlug string = ''

@description('GitHub OAuth application client ID.')
param githubOauthClientId string

@description('GitHub OAuth redirect URI.')
param githubOauthRedirectUri string

@description('OpenAI model for student-facing review conversation.')
param openAiModel string = 'gpt-5.6-sol'

@description('OpenAI model for semantic repository interpretation.')
param openAiRepositoryModel string = 'gpt-5.6-luna'

@description('OpenAI model for selective conversation-quality criticism.')
param openAiCriticModel string = 'gpt-5.6-luna'

@description('Optional initial Course Owner email. Empty disables bootstrap ownership.')
param bootstrapOwnerEmail string = ''

@description('Key Vault secret containing the PostgreSQL SQLAlchemy connection URL.')
param databaseUrlSecretName string = 'etis-database-url'

@description('Key Vault secret containing the ETIS session signing secret.')
param sessionSecretName string = 'etis-session-secret'

@description('Key Vault secret containing the Microsoft Entra client secret.')
param entraClientSecretName string = 'entra-client-secret'

@description('Key Vault secret containing the GitHub App private key.')
param githubAppPrivateKeySecretName string = 'github-app-private-key'

@description('Key Vault secret containing the GitHub OAuth client secret.')
param githubOauthClientSecretName string = 'github-oauth-client-secret'

@description('Key Vault secret containing the OpenAI API key.')
param openAiApiKeySecretName string = 'openai-api-key'

@minValue(0)
@maxValue(5)
@description('Minimum number of application replicas.')
param minReplicas int = 0

@minValue(1)
@maxValue(10)
@description('Maximum number of application replicas.')
param maxReplicas int = 5

var suffix = uniqueString(subscription().id, resourceGroup().id)
var compactPrefix = toLower(replace(prefix, '-', ''))

var acrName = take('${compactPrefix}${environment}${suffix}', 50)
var runtimeIdentityName = '${prefix}-${environment}-runtime'
var keyVaultName = take('${prefix}-${environment}-kv-${suffix}', 24)
var containerAppsEnvironmentName = '${prefix}-${environment}-cae'
var appName = '${prefix}-${environment}'

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

resource managedCertificate 'Microsoft.App/managedEnvironments/managedCertificates@2025-01-01' existing = {
  parent: containerAppsEnvironment
  name: managedCertificateName
}

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
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
      activeRevisionsMode: 'Single'

      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false

        customDomains: [
          {
            name: customDomainName
            bindingType: 'SniEnabled'
            certificateId: managedCertificate.id
          }
        ]
      }

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
        {
          name: 'session-secret'
          identity: runtimeIdentity.id
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${sessionSecretName}'
        }
        {
          name: 'entra-client-secret'
          identity: runtimeIdentity.id
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${entraClientSecretName}'
        }
        {
          name: 'github-app-private-key'
          identity: runtimeIdentity.id
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${githubAppPrivateKeySecretName}'
        }
        {
          name: 'github-oauth-client-secret'
          identity: runtimeIdentity.id
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${githubOauthClientSecretName}'
        }
        {
          name: 'openai-api-key'
          identity: runtimeIdentity.id
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${openAiApiKeySecretName}'
        }
      ]
    }

    template: {
      containers: [
        {
          name: 'studio'
          image: containerImage

          env: [
            {
              name: 'ETIS_ENV'
              value: 'production'
            }
            {
              name: 'ETIS_DEV_LOGIN'
              value: 'false'
            }
            {
              name: 'ETIS_WEB_ORIGIN'
              value: webOrigin
            }
            {
              name: 'ETIS_DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'ETIS_SESSION_SECRET'
              secretRef: 'session-secret'
            }
            {
              name: 'ETIS_COURSE_NAMESPACE'
              value: courseNamespace
            }
            {
              name: 'ETIS_INSTRUCTOR_GITHUB'
              value: instructorGithub
            }
            {
              name: 'ETIS_BOOTSTRAP_OWNER_EMAIL'
              value: bootstrapOwnerEmail
            }
            {
              name: 'ETIS_AI_ENABLED'
              value: 'true'
            }
            {
              name: 'ETIS_AI_USAGE_ENABLED'
              value: 'true'
            }

            {
              name: 'ENTRA_CLIENT_ID'
              value: entraClientId
            }
            {
              name: 'ENTRA_CLIENT_SECRET'
              secretRef: 'entra-client-secret'
            }
            {
              name: 'ENTRA_REDIRECT_URI'
              value: entraRedirectUri
            }
            {
              name: 'ENTRA_TENANT'
              value: entraTenant
            }
            {
              name: 'ENTRA_ALLOWED_DOMAIN'
              value: entraAllowedDomain
            }
            {
              name: 'ETIS_PRODUCTION_TEST_STUDENT_OID'
              value: productionTestStudentOid
            }
            {
              name: 'ETIS_PRODUCTION_TEST_STUDENT_EMAIL'
              value: productionTestStudentEmail
            }
            {
              name: 'ETIS_PRODUCTION_TEST_STUDENT_ID'
              value: productionTestStudentId
            }
            {
              name: 'ETIS_PRODUCTION_TEST_SECTION_KEY'
              value: productionTestSectionKey
            }
            {
              name: 'ETIS_PRODUCTION_TEST_TEAM_KEY'
              value: productionTestTeamKey
            }

            {
              name: 'GITHUB_APP_ID'
              value: githubAppId
            }
            {
              name: 'GITHUB_APP_PRIVATE_KEY'
              secretRef: 'github-app-private-key'
            }
            {
              name: 'GITHUB_APP_SLUG'
              value: githubAppSlug
            }
            {
              name: 'GITHUB_OAUTH_CLIENT_ID'
              value: githubOauthClientId
            }
            {
              name: 'GITHUB_OAUTH_CLIENT_SECRET'
              secretRef: 'github-oauth-client-secret'
            }
            {
              name: 'GITHUB_OAUTH_REDIRECT_URI'
              value: githubOauthRedirectUri
            }

            {
              name: 'OPENAI_API_KEY'
              secretRef: 'openai-api-key'
            }
            {
              name: 'OPENAI_MODEL'
              value: openAiModel
            }
            {
              name: 'OPENAI_REPOSITORY_MODEL'
              value: openAiRepositoryModel
            }
            {
              name: 'OPENAI_CRITIC_MODEL'
              value: openAiCriticModel
            }
          ]

          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
              successThreshold: 1
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/ready'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 6
              successThreshold: 1
            }
          ]

          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]

      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http'
            http: {
              metadata: {
                concurrentRequests: '25'
              }
            }
          }
        ]
      }
    }
  }
}

output containerAppName string = app.name
output containerAppFqdn string = app.properties.configuration.ingress.fqdn
output containerAppUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
