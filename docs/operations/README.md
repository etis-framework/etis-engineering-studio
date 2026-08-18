# ETIS Engineering Studio Operations and Recovery

## Purpose

This directory contains the production operations, incident-response, and
database-recovery procedures for the ETIS Engineering Studio.

These artifacts are part of **Gate 16 — Operations, Recovery, and Production
Readiness**.

Gate 16 deliberately separates:

- controls that can be proven during pre-deployment hardening;
- controls verified continuously in CI;
- controls that require post-provisioning Azure evidence;
- final production-access decisions owned by Gate 17.

The existence of infrastructure code or runbooks does not by itself authorize
student production use.

## Gate 16 artifacts

### `PRODUCTION_OPERATIONS_RUNBOOK.md`

Defines:

- `/health` and `/ready` interpretation;
- Application Insights and Log Analytics monitoring;
- Azure Monitor alert handling;
- operational escalation;
- maintenance procedures;
- initial RTO and RPO planning targets;
- production-readiness checks.

### `INCIDENT_RESPONSE_RUNBOOK.md`

Defines:

- incident severity;
- containment;
- credential handling;
- evidence preservation;
- student/instructor impact assessment;
- communication;
- recovery;
- fail-closed authority;
- post-incident review.

### `DATABASE_RECOVERY_RUNBOOK.md`

Defines:

- PostgreSQL point-in-time restore;
- restore to a new server;
- preservation of the original source;
- private-network validation;
- Alembic compatibility;
- Key Vault cutover;
- `/ready` validation;
- rollback;
- recovery evidence;
- RTO/RPO measurement.

## Pre-deployment evidence

The following Gate 16 controls can be established before any production Azure
resources exist:

- operational alert definitions as Bicep;
- explicit production alert thresholds;
- scale-to-zero-safe monitoring design;
- incident-response procedures;
- database-recovery procedures;
- production operations procedures;
- documented RTO/RPO planning targets;
- fail-closed recovery requirements;
- PostgreSQL logical backup/restore drill implementation;
- CI enforcement of the backup/restore drill;
- automated regression contracts for these controls.

This is **pre-deployment** evidence.

It proves that the required operational controls are designed, versioned,
testable, and reproducible.

It does not prove that a live Azure resource actually delivered an alert or
completed a recovery.

## CI evidence

GitHub CI provides repeatable evidence for controls that do not require live
production Azure resources.

Gate 16 CI evidence includes:

- Python regression tests;
- Gate 16 operational-readiness contract tests;
- Bicep compilation;
- PostgreSQL/Alembic migration validation;
- production container smoke testing;
- PostgreSQL logical backup;
- PostgreSQL logical restore;
- restored Alembic revision validation;
- restored sentinel-data validation.

The logical backup/restore drill validates that the application's production
schema can be dumped and restored correctly with PostgreSQL tooling.

It does not replace Azure Flexible Server point-in-time restore validation.

## Post-provisioning evidence

Some controls cannot honestly be proven before Azure resources exist.

After production infrastructure is provisioned, Gate 16 requires
**post-provisioning** evidence for at least:

1. Application Insights receives expected bounded telemetry.
2. Log Analytics receives expected bounded operational logging.
3. The Azure Monitor action group reaches the intended operator address.
4. The Container App restart alert exists and can be inspected.
5. The Container App HTTP 5xx alert exists and can be inspected.
6. The PostgreSQL `is_db_alive` alert exists and can be inspected.
7. The PostgreSQL `storage_percent` alert exists and can be inspected.
8. `/health` behaves as documented.
9. `/ready` behaves as documented.
10. PostgreSQL backup configuration matches the intended retention posture.
11. A live PostgreSQL Flexible Server **point-in-time restore** is performed.
12. The restore creates and validates a separate recovery server.
13. Private networking is preserved for the restored server.
14. Alembic/database compatibility is verified.
15. Application readiness is demonstrated against the recovery candidate.
16. Actual recovery duration is recorded.
17. Actual observed RTO/RPO evidence is recorded.
18. Rollback/cutover procedure is reviewed.

The live point-in-time restore exercise must produce evidence; it must not be
treated as complete merely because Azure documentation states that restore is
supported.

## Suggested Gate 16 evidence record

For each post-provisioning verification, capture:

- date/time;
- operator;
- Azure resource;
- relevant Git SHA;
- action performed;
- expected result;
- actual result;
- evidence reference;
- pass/fail;
- follow-up required.

Do not place credentials, access tokens, database passwords, API keys, session
cookies, or unnecessary student information in the evidence record.

## Gate 16 exit condition

Gate 16 can be considered technically implemented before deployment when:

- all Gate 16 source-controlled controls exist;
- all Gate 16 automated contracts pass;
- CI executes the PostgreSQL backup/restore drill;
- CI compiles the operational Bicep;
- operations/recovery documentation is complete.

However, **production operational readiness remains conditional** until the
required post-provisioning evidence is collected.

This distinction prevents the project from claiming that Azure alert delivery,
live backup recovery, or production telemetry have been tested when Azure has
not yet been provisioned.

## Gate 17 relationship

**Gate 17 — Final Pre-Azure Go/No-Go** consumes the pre-deployment evidence from
all prior gates and decides whether production Azure provisioning may begin.

At Gate 17, each production control must be identified as one of:

- proven;
- verified in CI;
- requires post-provisioning validation;
- blocked;
- deferred with explicit acceptance.

Gate 17 must not classify a live Azure control as verified when the production
resources required to test that control do not yet exist.

An explicit Gate 17 GO authorizes Azure provisioning and deployment. It does
**not** authorize student production use.

After provisioning, the required Gate 16 live evidence must be collected and
evaluated through a separate **Post-Provisioning Production Acceptance**
review. That review must verify the required telemetry, alerting, health,
readiness, backup, point-in-time recovery, networking, authentication,
authorization, DNS, and other live production controls before student access is
enabled.

A successful deployment is not itself a go-live decision.

A successful `/ready` response is necessary but not sufficient for student
production authorization.

Student access remains disabled until Post-Provisioning Production Acceptance
reaches an explicit GO.
