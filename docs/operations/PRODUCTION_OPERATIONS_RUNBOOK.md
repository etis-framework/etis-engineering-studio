# ETIS Engineering Studio Production Operations Runbook

> **Status:** Current production runbook. Post-Provisioning Production Acceptance is **GO** as of 2026-08-21.

## 1. Purpose

This runbook defines the normal production operating procedure for the ETIS
Engineering Studio.

It covers:

- service-health interpretation;
- Azure monitoring;
- alert triage;
- escalation;
- routine maintenance;
- deployment verification;
- recovery objectives;
- privacy-safe operational handling.

This document is an operator runbook, not an application architecture
specification and not an incident-forensics record.

Security and privacy boundaries remain authoritative in
`docs/SECURITY_AND_PRIVACY.md`.

## 2. Operating model

The initial production service is intentionally small:

- Azure Container Apps hosts the Engineering Studio application;
- Azure Database for PostgreSQL Flexible Server stores durable application data;
- Azure Key Vault stores runtime secrets;
- Azure Container Registry stores production images;
- Log Analytics receives operational telemetry;
- Application Insights provides application-observability views;
- Azure Monitor alerts operators when selected runtime or database conditions
  require attention.

The accepted semester runtime keeps **one minimum replica** warm and allows up to five replicas. A zero-instance state is therefore not expected during normal accepted production operation. Treat unexpected loss of ready replicas together with `/ready`, restart, 5xx, and Azure resource state as an availability signal.

Production operation must remain fail closed where authority, identity,
database state, evidence integrity, or engineering records are uncertain.

## 3. Health endpoints

### `/health`

`/health` indicates that the application process is running and exposes bounded
configuration/feature readiness information.

Use `/health` to distinguish basic process availability from durable-service
readiness.

A successful `/health` response does **not** prove:

- PostgreSQL connectivity;
- current database migration state;
- successful Microsoft Entra authentication;
- successful GitHub access;
- successful OpenAI access;
- complete end-to-end student functionality.

### `/ready`

`/ready` is the authoritative application traffic-readiness endpoint.

The service is ready only when:

- PostgreSQL is reachable; and
- the database Alembic revision equals the application Alembic head.

Expected successful fields include:

- `"status": "ready"`
- `"database_connected": true`
- `"migration_current": true`

A failure returns HTTP 503 with `"status": "not_ready"`.

A failing `/ready` endpoint must be treated as an application or database
readiness problem even when `/health` still returns successfully.

## 4. Primary monitoring surfaces

### Application Insights

Use Application Insights for application-centric investigation such as:

- request failures;
- request duration;
- status-code trends;
- application availability symptoms;
- correlation around an incident window.

Application telemetry must remain within the bounded logging policy defined in
`docs/SECURITY_AND_PRIVACY.md`.

### Log Analytics

Use Log Analytics for centralized operational log investigation and correlation.

Normal telemetry may include bounded fields such as:

- request ID;
- HTTP method;
- route template;
- response status;
- duration;
- bounded error type.

Do not intentionally log:

- session credentials;
- bearer tokens;
- OAuth authorization codes;
- cookies;
- passwords;
- API keys;
- request bodies;
- complete prompts;
- complete model responses;
- unnecessary student email addresses;
- unnecessary repository evidence.

## 5. Production alert set

Gate 16 defines four initial Azure Monitor signals.

### Container App — `RestartCount`

Purpose:

Detect application replica instability or repeated process/container failure.

Initial trigger:

- one or more restarts within the configured evaluation window.

Operator response:

1. inspect deployment/revision state;
2. inspect application logs near the restart;
3. verify `/health`;
4. verify `/ready`;
5. determine whether the restart was transient, configuration-related, or
   repeated;
6. escalate repeated or unexplained restarts.

Do not treat instance count alone as the only availability signal. Correlate restart count with `/ready`, HTTP failures, revision health, and Azure resource state.

### Container App — HTTP `5xx`

Purpose:

Detect server-side request failures visible to users.

Initial trigger:

- one or more requests in the `5xx` status-code category during the configured
  evaluation window.

Operator response:

1. determine affected routes and time range;
2. examine correlated request IDs;
3. check `/ready`;
4. check deployment/revision changes;
5. check database health;
6. determine whether failures are isolated or systematic;
7. escalate systematic failures.

### PostgreSQL — `is_db_alive`

Purpose:

Detect when PostgreSQL Flexible Server reports that the database is unavailable.

This is a high-severity condition.

Operator response:

1. confirm the Azure resource state;
2. verify whether `/ready` is returning 503;
3. inspect Azure PostgreSQL health information;
4. determine whether maintenance, networking, resource failure, or another
   database condition is involved;
5. do not bypass database readiness checks to restore traffic;
6. begin the database recovery procedure if normal service cannot be restored.

### PostgreSQL — `storage_percent`

Purpose:

Provide advance warning before storage pressure threatens database availability.

Initial warning threshold:

- 80 percent storage utilization.

Operator response:

1. confirm current utilization and trend;
2. determine whether growth is expected;
3. inspect unusual data growth;
4. review storage/autogrow configuration;
5. increase capacity before an emergency condition develops if justified;
6. investigate unexpected growth rather than treating capacity expansion as the
   only response.

## 6. Alert ownership and escalation

The configured production operations alert address is the initial operational
notification destination.

An alert must be acknowledged by an authorized operator.

### Immediate escalation conditions

Escalate immediately when any of the following occurs:

- suspected credential compromise;
- suspected unauthorized access;
- possible exposure of student or engineering-record data;
- database unavailability that does not recover promptly;
- loss or suspected corruption of durable engineering records;
- repeated production crashes;
- systemic 5xx failures;
- failed production migration;
- inability to establish trusted system state after a deployment;
- evidence that access controls are not failing closed.

### Normal operational escalation

For lower-severity conditions:

1. establish scope;
2. preserve useful diagnostic evidence;
3. determine user impact;
4. attempt only bounded, reversible remediation;
5. escalate when the cause is unclear or the condition persists.

Operators must not improvise destructive database repair or delete engineering
records as a troubleshooting shortcut.

## 7. Initial recovery objectives

The initial production deployment adopts engineering targets for operational
planning.

These targets are **not an SLA** and do not create a contractual service
commitment.

### RTO

Initial recovery-time objective (**RTO**) target:

- restore core Engineering Studio service within **4 hours** of a confirmed
  production outage requiring recovery action.

This target is intended to support a university-course workload rather than a
24x7 commercial service.

### RPO

Initial recovery-point objective (**RPO**) target:

- no more than **24 hours** of durable database state at risk for a recovery
  that requires use of PostgreSQL backup capabilities.

Actual achievable RPO may be better because Azure PostgreSQL Flexible Server
provides managed backup and point-in-time restore capabilities. The production
configuration and live restore exercise must establish the actual recoverable
window.

The RTO and RPO targets must be reviewed after the first live Azure recovery
exercise and after meaningful changes to workload importance or operating
hours.

## 8. Normal deployment verification

The authorized GitHub Actions production workflow is the normal deployment path.

After a production deployment:

1. confirm the release gate succeeded;
2. confirm foundation reconciliation succeeded;
3. confirm Key Vault secret provisioning succeeded;
4. confirm the immutable Git-SHA image was pushed;
5. confirm the migration job succeeded;
6. confirm the application deployment succeeded;
7. confirm operational-control reconciliation succeeded;
8. confirm `/ready` reports ready;
9. confirm `migration_current=true`;
10. inspect Azure Monitor for immediate new failures.

Do not treat successful resource deployment alone as proof of application
readiness.

## 9. Routine maintenance

Routine maintenance includes:

- dependency and security updates through the normal repository/CI process;
- review of PostgreSQL storage growth;
- review of alert history;
- review of Container App restart patterns;
- review of sustained 5xx activity;
- verification that production secrets remain in Key Vault;
- verification that GitHub production-environment protection remains enabled;
- review of Azure SKU and cost posture;
- review of backup configuration;
- periodic execution of the documented recovery exercise.

All application changes must continue through normal source-control, review,
testing, and deployment controls.

Do not make ad hoc production code edits or manually modify a running container.

## 10. Planned maintenance procedure

For planned maintenance that could affect students:

1. determine expected user impact;
2. choose an appropriate course-maintenance window;
3. preserve current production state and deployment identity;
4. communicate material impact through the appropriate course channel;
5. execute the controlled change;
6. verify `/health`;
7. verify `/ready`;
8. verify authentication and one representative authorized workflow when
   applicable;
9. verify monitoring after the change;
10. document unexpected behavior.

Sakai remains the authoritative course-announcement channel when student
communication is required.

## 11. Database maintenance boundary

Production schema lifecycle is owned by Alembic.

Do not:

- run `create_all()` as a production schema-management mechanism;
- manually edit production tables to approximate a migration;
- skip failed migrations and force a new application revision live;
- destroy the source database during recovery investigation.

The production deployment workflow must stop when migration execution fails.

Database recovery is governed by
`docs/operations/DATABASE_RECOVERY_RUNBOOK.md`.

## 12. Incident boundary

Conditions involving security, privacy, integrity, substantial outage, or
uncertain authority are incidents rather than routine maintenance.

Use:

`docs/operations/INCIDENT_RESPONSE_RUNBOOK.md`

Routine troubleshooting must transition to the incident procedure once the
operator can no longer establish trustworthy normal system state.

## 13. Evidence preservation

Operational evidence useful to diagnosis may include:

- alert timestamp and identifier;
- affected Azure resource;
- deployment Git SHA;
- Container App revision;
- migration execution identity;
- request IDs;
- bounded Azure Monitor queries/results;
- database resource-health state;
- operator actions and timestamps.

Evidence preservation must follow the security and privacy rules in
`docs/SECURITY_AND_PRIVACY.md`.

Do not collect sensitive payloads merely because an incident exists.

## 14. Production-readiness review

Before student access is enabled, operations readiness must verify:

- production alert destination is correct;
- action group notifications are received;
- all four Gate 16 alerts exist and are enabled;
- Application Insights is receiving expected telemetry;
- Log Analytics is receiving expected telemetry;
- `/health` behaves as documented;
- `/ready` behaves as documented;
- PostgreSQL backup settings are verified;
- the live Azure point-in-time restore exercise has been completed;
- incident and recovery runbooks have been reviewed;
- escalation ownership is known;
- GitHub production deployment protection is active;
- operational evidence is retained for Post-Provisioning Production Acceptance.

## 15. Gate 16 / Gate 17 closeout

Gate 16 established the operational controls and procedures required for production use. Gate 17 authorized Azure provisioning. Post-Provisioning Production Acceptance subsequently exercised the live controls and reached **GO** on 2026-08-21.

Current operators should use this runbook together with:

- `docs/PRODUCTION_BASELINE.md`;
- `docs/operations/POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md`;
- `docs/operations/INCIDENT_RESPONSE_RUNBOOK.md`;
- `docs/operations/DATABASE_RECOVERY_RUNBOOK.md`.

A successful deployment or `/ready` response is still not, by itself, sufficient evidence for a future production-changing release. Future changes require the normal PR/CI/protected-deployment/targeted-acceptance cycle.
