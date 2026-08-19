targetScope = 'resourceGroup'

@description('Azure region. Must match the ETIS production deployment.')
param location string = resourceGroup().location

@description('Resource-name prefix. Must match the foundation deployment.')
param prefix string = 'etis-studio'

@description('Deployment environment name. Must match the foundation deployment.')
param environment string = 'prod'

@description('Email address that receives production Azure Monitor alerts.')
param operationsAlertEmail string

@minValue(1)
@maxValue(100)
@description('5xx requests in a five-minute window that trigger an alert.')
param application5xxThreshold int = 1

@minValue(1)
@maxValue(100)
@description('Replica restart count that triggers an operational alert.')
param restartCountThreshold int = 1

@minValue(50)
@maxValue(95)
@description('PostgreSQL storage utilization percentage that triggers a warning.')
param postgresStoragePercentThreshold int = 80

var suffix = uniqueString(subscription().id, resourceGroup().id)
var appName = '${prefix}-${environment}'
var postgresServerName = take('${prefix}-${environment}-pg-${suffix}', 63)
var actionGroupName = '${prefix}-${environment}-operations'
var actionGroupShortName = 'etis-prod'

resource app 'Microsoft.App/containerApps@2025-01-01' existing = {
  name: appName
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' existing = {
  name: postgresServerName
}

resource operationsActionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  properties: {
    enabled: true
    groupShortName: actionGroupShortName

    emailReceivers: [
      {
        name: 'ETIS production operations'
        emailAddress: operationsAlertEmail
        useCommonAlertSchema: true
      }
    ]

    armRoleReceivers: []
    automationRunbookReceivers: []
    azureAppPushReceivers: []
    azureFunctionReceivers: []
    eventHubReceivers: []
    itsmReceivers: []
    logicAppReceivers: []
    smsReceivers: []
    voiceReceivers: []
    webhookReceivers: []
  }
}

// RestartCount is intentionally used instead of instance-count monitoring.
// The application permits scale-to-zero, so zero active instances is not
// itself an outage condition.
resource appRestartAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${prefix}-${environment}-container-restarts'
  location: 'global'
  properties: {
    description: 'ETIS production Container App replica restart count requires operational review.'
    severity: 2
    enabled: true
    autoMitigate: true
    scopes: [
      app.id
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'

    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'ContainerRestartCount'
          metricNamespace: 'Microsoft.App/containerApps'
          metricName: 'RestartCount'
          dimensions: []
          operator: 'GreaterThanOrEqual'
          threshold: restartCountThreshold
          timeAggregation: 'Maximum'
          skipMetricValidation: false
        }
      ]
    }

    actions: [
      {
        actionGroupId: operationsActionGroup.id
      }
    ]
  }
}

resource app5xxAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${prefix}-${environment}-http-5xx'
  location: 'global'
  properties: {
    description: 'ETIS production Container App is returning HTTP 5xx responses.'
    severity: 1
    enabled: true
    autoMitigate: true
    scopes: [
      app.id
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'

    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'Application5xx'
          metricNamespace: 'Microsoft.App/containerApps'
          metricName: 'Requests'
          dimensions: [
            {
              name: 'statusCodeCategory'
              operator: 'Include'
              values: [
                '5xx'
              ]
            }
          ]
          operator: 'GreaterThanOrEqual'
          threshold: application5xxThreshold
          timeAggregation: 'Total'
          skipMetricValidation: false
        }
      ]
    }

    actions: [
      {
        actionGroupId: operationsActionGroup.id
      }
    ]
  }
}

resource postgresAliveAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${prefix}-${environment}-postgres-not-alive'
  location: 'global'
  properties: {
    description: 'ETIS production PostgreSQL Flexible Server reports that the database is not alive.'
    severity: 0
    enabled: true
    autoMitigate: true
    scopes: [
      postgres.id
    ]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'

    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'PostgresDatabaseAlive'
          metricNamespace: 'Microsoft.DBforPostgreSQL/flexibleServers'
          metricName: 'is_db_alive'
          dimensions: []
          operator: 'LessThan'
          threshold: 1
          timeAggregation: 'Minimum'
          skipMetricValidation: false
        }
      ]
    }

    actions: [
      {
        actionGroupId: operationsActionGroup.id
      }
    ]
  }
}

resource postgresStorageAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${prefix}-${environment}-postgres-storage'
  location: 'global'
  properties: {
    description: 'ETIS production PostgreSQL storage utilization is approaching capacity.'
    severity: 2
    enabled: true
    autoMitigate: true
    scopes: [
      postgres.id
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'

    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'PostgresStoragePercent'
          metricNamespace: 'Microsoft.DBforPostgreSQL/flexibleServers'
          metricName: 'storage_percent'
          dimensions: []
          operator: 'GreaterThanOrEqual'
          threshold: postgresStoragePercentThreshold
          timeAggregation: 'Average'
          skipMetricValidation: false
        }
      ]
    }

    actions: [
      {
        actionGroupId: operationsActionGroup.id
      }
    ]
  }
}

output operationsActionGroupName string = operationsActionGroup.name
output operationsActionGroupId string = operationsActionGroup.id
