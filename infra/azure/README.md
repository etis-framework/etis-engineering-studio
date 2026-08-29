# ETIS Engineering Studio Azure Infrastructure

> **Status:** Source-controlled production IaC. The current Azure environment was provisioned and Post-Provisioning Production Acceptance reached **GO** on 2026-08-21.

This directory contains the Bicep templates used by the protected production deployment workflow.

## Files

### `main.bicep`

Creates the long-lived production foundation:

- VNet and Container Apps/PostgreSQL subnets;
- PostgreSQL private DNS zone/link;
- Log Analytics;
- workspace-based Application Insights;
- ACR;
- user-assigned runtime managed identity;
- Key Vault and RBAC;
- Container Apps managed environment;
- PostgreSQL Flexible Server/database.

### `secrets.bicep`

Writes protected deployment inputs into Key Vault for:

- database URL;
- session secret;
- Entra client secret;
- GitHub App private key;
- GitHub OAuth client secret;
- OpenAI API key.

Secret values must never be committed.

### `migration.bicep`

Creates the Container Apps migration job that runs the immutable application image and `alembic upgrade head` inside the private network.


### v0.17 reasoning-validation rollout

The manual `Deploy Azure` workflow includes an explicit `reasoning_validation_mode` choice for newly started review sessions:

- `legacy` (default) — no shadow validator calls;
- `shadow` — independent reasoning validation runs on analytically material turns while the legacy engine remains student-authoritative.

The workflow passes the selected value into `app.bicep`, which persists `ETIS_REASONING_VALIDATION_MODE` in the Container App. The validator model is configured as `OPENAI_REASONING_VALIDATOR_MODEL` and defaults to `gpt-5.6-luna`. Existing active review sessions retain their session-locked analytical mode even when a later deployment changes the default for new sessions.

### `app.bicep`

Defines the production Container App:

- public HTTPS ingress/custom domain;
- managed identity;
- ACR image pull;
- Key Vault-backed secrets;
- Entra/GitHub/OpenAI production configuration;
- `/health` and `/ready` probes;
- horizontal scaling.

### `operations.bicep`

Defines the production action group and metric alerts for:

- Container App restart count;
- HTTP 5xx;
- PostgreSQL availability;
- PostgreSQL storage percentage.

## Deployment order

The protected manual workflow in `.github/workflows/deploy-azure.yml` follows this intent:

`release gate → foundation/secrets → immutable image → migration → application → operational controls → readiness verification`

The release gate installs a pinned Bicep CLI and compiles the templates before Azure deployment authority is used.

## CI validation

CI validates production configuration without live deployment authority, including:

- Bicep compilation;
- migrations;
- PostgreSQL-specific tests;
- production-container smoke;
- `/ready` behavior;
- application regression tests.

CI cannot by itself prove live DNS/TLS, Key Vault RBAC, alert configuration, PITR recovery, or GitHub/Entra behavior; those were exercised during Post-Provisioning Production Acceptance.

## Runtime identity and secrets

Application runtime uses a user-assigned managed identity with bounded ACR pull and Key Vault secret-read authority. Key Vault remains the source of production secret values; Container App environment variables use secret references rather than literal secrets.

## Database boundary

PostgreSQL is private-networked through delegated subnet/private DNS. Public network access is disabled. Alembic owns schema lifecycle; application startup does not silently migrate production.

Accepted live database posture is documented in `../../docs/PRODUCTION_BASELINE.md`.

## Scaling note — current source/runtime drift

The accepted production runtime is:

- `minReplicas=1`;
- `maxReplicas=5`.

`app.bicep` defaults `minReplicas` to `1` for the production deployment so one application replica remains warm and student access does not incur a scale-from-zero cold start. The accepted production scaling baseline is `minReplicas=1` and `maxReplicas=5`.

## Production boundary

Gate 17 is closed and Post-Provisioning Production Acceptance is GO. Future production changes still require:

1. branch/PR review;
2. CI/release gate;
3. protected manual deployment;
4. targeted live acceptance of the changed boundary.

No infrastructure requirement should be weakened merely to simplify local development or deployment.


### v0.17 shadow review-planning rollout

The manual `Deploy Azure` workflow also includes an explicit `review_planning_mode` choice for newly started review sessions:

- `legacy` (default) — the current semantic engine remains the only question-selection path;
- `shadow` — after PR2 shadow reasoning validation, the Studio generates candidate next moves, deterministically selects one, and realizes one internal comparison question while the legacy question remains student-visible.

Planning `shadow` requires reasoning validation `shadow`; incompatible configuration fails closed. Both modes are persisted into each new review session, so changing a later deployment default never changes analytical authority inside an active conversation. `OPENAI_REVIEW_PLANNER_MODEL` may override the shadow planner/realizer model; otherwise the critic model is used before falling back to the primary conversation model.
