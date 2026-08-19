targetScope = 'resourceGroup'

@description('Resource-name prefix. Must match the foundation deployment.')
param prefix string = 'etis-studio'

@description('Deployment environment name. Must match the foundation deployment.')
param environment string = 'prod'

@description('PostgreSQL administrator login. Must match the foundation deployment.')
param postgresAdminUser string = 'etisadmin'

@secure()
@description('PostgreSQL administrator password.')
param postgresAdminPassword string

@description('Application PostgreSQL database name. Must match the foundation deployment.')
param postgresDbName string = 'etis_studio'

@secure()
@minLength(32)
@description('ETIS production session signing secret.')
param sessionSecret string

@secure()
@description('Microsoft Entra application client secret.')
param entraClientSecret string

@secure()
@description('GitHub App private key.')
param githubAppPrivateKey string

@secure()
@description('GitHub OAuth application client secret.')
param githubOauthClientSecret string

@secure()
@description('OpenAI API key.')
param openAiApiKey string

var suffix = uniqueString(subscription().id, resourceGroup().id)
var keyVaultName = take('${prefix}-${environment}-kv-${suffix}', 24)
var postgresServerName = take('${prefix}-${environment}-pg-${suffix}', 63)

resource keyVault 'Microsoft.KeyVault/vaults@2025-05-01' existing = {
  name: keyVaultName
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' existing = {
  name: postgresServerName
}

// Encode credentials before embedding them in the SQLAlchemy URI so
// punctuation in generated/operator-provided credentials cannot alter
// connection-string structure.
var databaseUrl = 'postgresql+psycopg://${uriComponent(postgresAdminUser)}:${uriComponent(postgresAdminPassword)}@${postgres.properties.fullyQualifiedDomainName}:5432/${postgresDbName}?sslmode=require'

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: keyVault
  name: 'etis-database-url'
  properties: {
    contentType: 'ETIS PostgreSQL SQLAlchemy URL'
    value: databaseUrl
  }
}

resource sessionSecretResource 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: keyVault
  name: 'etis-session-secret'
  properties: {
    contentType: 'ETIS session signing secret'
    value: sessionSecret
  }
}

resource entraClientSecretResource 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: keyVault
  name: 'entra-client-secret'
  properties: {
    contentType: 'Microsoft Entra client secret'
    value: entraClientSecret
  }
}

resource githubAppPrivateKeyResource 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: keyVault
  name: 'github-app-private-key'
  properties: {
    contentType: 'GitHub App private key'
    value: githubAppPrivateKey
  }
}

resource githubOauthClientSecretResource 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: keyVault
  name: 'github-oauth-client-secret'
  properties: {
    contentType: 'GitHub OAuth client secret'
    value: githubOauthClientSecret
  }
}

resource openAiApiKeyResource 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: keyVault
  name: 'openai-api-key'
  properties: {
    contentType: 'OpenAI API key'
    value: openAiApiKey
  }
}
