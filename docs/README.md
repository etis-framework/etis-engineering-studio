# ETIS Engineering Studio Documentation Map

This directory contains the durable architecture, security, deployment, operations, acceptance, and product documentation for ETIS Engineering Studio.

> **Current status:** Production Post-Provisioning Acceptance reached **GO** on 2026-08-21. Documents that describe Gate 17 or pre-provisioning requirements are retained as historical decision/evidence records and are explicitly marked as such.

## Start here

For institutional/public use:

- [`INSTITUTIONAL_ADOPTION.md`](INSTITUTIONAL_ADOPTION.md) — institution-owned deployment and adoption path.
- [`PUBLIC_DEPLOYMENT_SECURITY.md`](PUBLIC_DEPLOYMENT_SECURITY.md) — security checklist for independent deployments.
- [`PUBLIC_RELEASE_CHECKLIST.md`](PUBLIC_RELEASE_CHECKLIST.md) — upstream repository-publication checklist.

For the ETIS Framework reference deployment:

- [`PRODUCTION_BASELINE.md`](PRODUCTION_BASELINE.md) — current accepted production topology, controls, live evidence, and residual notes.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — current system architecture and trust boundaries.
- [`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md) — security, privacy, retention, and semester-lifecycle policy.
- [`AZURE_DEPLOYMENT.md`](AZURE_DEPLOYMENT.md) — production deployment, GitHub App, Entra, Azure, and runtime configuration.
- [`LOCAL_DEVELOPMENT.md`](LOCAL_DEVELOPMENT.md) — local developer workflow.
- [`PRODUCT_EXPERIENCE.md`](PRODUCT_EXPERIENCE.md) — student and instructor product behavior.
- [`WAVE1_ACCEPTANCE.md`](WAVE1_ACCEPTANCE.md) — Wave 1 acceptance status and evidence classification.
- [`NEXT_BUILD.md`](NEXT_BUILD.md) — deliberately deferred maintenance/enhancement backlog after production freeze.

## Architecture detail

The files under [`architecture/`](architecture/) document the specialized design contracts behind the current product:

- conversation engine and semantic coaching;
- repository intelligence and review orchestration;
- evidence packages and AI economics;
- review modes, finding lifecycle, and evidence scope;
- identity, course administration, and team/repository onboarding;
- Engineering Evidence and review continuity;
- interaction integrity and product hardening;
- conversation quality/evaluation policy.

These are design contracts, not step-by-step operator procedures.

## Production operations

Start with [`operations/README.md`](operations/README.md).

Current operational documents include:

- [`operations/PRODUCTION_OPERATIONS_RUNBOOK.md`](operations/PRODUCTION_OPERATIONS_RUNBOOK.md)
- [`operations/INCIDENT_RESPONSE_RUNBOOK.md`](operations/INCIDENT_RESPONSE_RUNBOOK.md)
- [`operations/DATABASE_RECOVERY_RUNBOOK.md`](operations/DATABASE_RECOVERY_RUNBOOK.md)
- [`operations/POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md`](operations/POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md)

Historical Gate 17 records are retained because they capture the security, retention, cost, and pre-Azure decisions that constrained production provisioning:

- [`GATE17_PRE_AZURE_GO_NO_GO.md`](GATE17_PRE_AZURE_GO_NO_GO.md)
- [`operations/GATE17_PRODUCTION_SECURITY_REVIEW.md`](operations/GATE17_PRODUCTION_SECURITY_REVIEW.md)
- [`operations/GATE17_RETENTION_DECISION.md`](operations/GATE17_RETENTION_DECISION.md)
- [`operations/GATE17_COST_CONTROL_PLAN.md`](operations/GATE17_COST_CONTROL_PLAN.md)

Do not treat an old “not yet testable” statement inside a historical gate record as the current production status. Current live results are in `PRODUCTION_BASELINE.md`, `BUILD_REPORT.md`, and the Post-Provisioning Production Acceptance record.

## Course model

The authoritative course-source precedence is summarized in [`../course-model/source-manifest.md`](../course-model/source-manifest.md). Machine-readable phase contracts remain under `course-model/`.

## Repository-level policy

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md)
- [`../GOVERNANCE.md`](../GOVERNANCE.md)
- [`../SECURITY.md`](../SECURITY.md)
- [`../SUPPORT.md`](../SUPPORT.md)
- [`../LICENSE`](../LICENSE) and [`../NOTICE`](../NOTICE)
- [`../TRADEMARKS.md`](../TRADEMARKS.md)
- [`../CITATION.cff`](../CITATION.cff)
- [`../CHANGELOG.md`](../CHANGELOG.md)
- [`../BUILD_REPORT.md`](../BUILD_REPORT.md)

## Documentation maintenance rule

When a production behavior changes, update the durable document that owns that behavior in the same PR. Do not create new root-level patch-note or patch-manifest overlays. Git history and `CHANGELOG.md` are the release history.
