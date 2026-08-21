# ETIS Engineering Studio Operations and Recovery

> **Status:** Production operational readiness is **GO** as of 2026-08-21.

This directory contains the production runbooks, recovery procedures, live
acceptance evidence, and historical gate records used to operate ETIS
Engineering Studio.

## Gate 16 and Gate 17 relationship

These artifacts originated in **Gate 16 — Operations, Recovery, and Production
Readiness** and were consumed by **Gate 17 — Final Pre-Azure Go/No-Go**.

Gate 16 deliberately separated:

- controls proven during **pre-deployment** hardening;
- controls continuously verified in CI;
- controls requiring **post-provisioning** Azure **evidence**;
- final production-access decisions.

An explicit Gate 17 GO authorized Azure provisioning/deployment. It did not by
itself authorize normal student production use. After provisioning, the live
Gate 16 evidence was collected and evaluated through Post-Provisioning
Production Acceptance, which reached GO on 2026-08-21.

## Current operator documents

### `PRODUCTION_OPERATIONS_RUNBOOK.md`

Day-to-day production operation, `/health` and `/ready` interpretation,
telemetry, alert handling, deployment/rollback posture, semester operation, and
evidence collection.

### `INCIDENT_RESPONSE_RUNBOOK.md`

Incident declaration, triage, containment, credential response, evidence
preservation, communication, and recovery.

### `DATABASE_RECOVERY_RUNBOOK.md`

PostgreSQL backup and **point-in-time restore** procedure, restore to a separate
server, private-network validation, Alembic compatibility, Key Vault cutover,
`/ready` validation, rollback, and RTO/RPO measurement. A real non-destructive
production point-in-time restore exercise passed on 2026-08-21.

### `POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md`

The live acceptance control set, post-provisioning evidence, and the 2026-08-21
GO decision record.

## Historical gate records

These documents are retained as decision history, not current to-do lists:

- `GATE17_PRODUCTION_SECURITY_REVIEW.md`
- `GATE17_RETENTION_DECISION.md`
- `GATE17_COST_CONTROL_PLAN.md`
- `../GATE17_PRE_AZURE_GO_NO_GO.md`

The historical records explain what was planned/proven before Azure authority
was granted; the post-provisioning record explains what was verified live.

## Current live baseline

See `../PRODUCTION_BASELINE.md` for the concise accepted live topology and
control state.

Key accepted operations evidence includes:

- managed identity + Key Vault secret references;
- private PostgreSQL;
- `/health` and `/ready` PASS;
- Application Insights + Log Analytics;
- production Azure Monitor alerts/action group;
- 7-day PostgreSQL PITR;
- successful real point-in-time restore drill;
- immutable ACR rollback images;
- `$100/month` production budget with 50/80/100% notifications;
- one minimum warm Container App replica and five maximum replicas.

## Operational rule

Do not make emergency changes silently. If Azure runtime state is changed
outside source control, document it and reconcile the source-controlled
IaC/configuration in a later controlled PR.
