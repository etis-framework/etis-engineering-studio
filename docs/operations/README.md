# ETIS Engineering Studio Operations and Recovery

> **Status:** Production operational readiness is **GO** as of 2026-08-21.

This directory contains the runbooks and historical gate records used to operate ETIS Engineering Studio in production.

## Current operator documents

### `PRODUCTION_OPERATIONS_RUNBOOK.md`

Day-to-day production operation, health/readiness interpretation, telemetry, alert handling, deployment/rollback posture, semester operation, and evidence collection.

### `INCIDENT_RESPONSE_RUNBOOK.md`

Incident declaration, triage, containment, credential response, evidence preservation, communication, and recovery.

### `DATABASE_RECOVERY_RUNBOOK.md`

PostgreSQL backup/PITR recovery procedure. A real non-destructive production PITR exercise passed on 2026-08-21.

### `POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md`

The live acceptance control set and the 2026-08-21 GO decision record.

## Historical Gate 17 records

These documents are retained as decision history, not current “to-do” lists:

- `GATE17_PRODUCTION_SECURITY_REVIEW.md`
- `GATE17_RETENTION_DECISION.md`
- `GATE17_COST_CONTROL_PLAN.md`
- `../GATE17_PRE_AZURE_GO_NO_GO.md`

Gate 17 authorized Azure provisioning. Post-Provisioning Production Acceptance separately authorized normal student production use.

## Current live baseline

See `../PRODUCTION_BASELINE.md` for the concise accepted live topology and control state.

Key accepted operations evidence includes:

- managed identity + Key Vault secret references;
- private PostgreSQL;
- `/health` and `/ready` PASS;
- Application Insights + Log Analytics;
- production Azure Monitor alerts/action group;
- 7-day PostgreSQL PITR;
- successful real PITR restore drill;
- immutable ACR rollback images;
- `$100/month` production budget with 50/80/100% notifications;
- one minimum warm Container App replica and five maximum replicas.

## Operational rule

Do not make emergency changes silently. If Azure runtime state is changed outside source control, document it and reconcile the source-controlled IaC/configuration in a later controlled PR.
