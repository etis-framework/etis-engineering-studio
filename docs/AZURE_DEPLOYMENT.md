# Azure Deployment and Production Configuration

> **Institutional adoption:** names, domains, tenant values, resource identifiers, budgets, and settings in this document describe the ETIS Framework reference deployment. Create institution-owned equivalents; do not reuse reference production credentials or identifiers.

> **Status:** Production deployed and accepted. Gate 17 is closed; Post-Provisioning Production Acceptance reached **GO** on 2026-08-21.

## Purpose

This document describes the source-controlled deployment path and the current production configuration for ETIS Engineering Studio. It replaces the earlier pre-Azure posture in which these resources were only planned.

The authoritative production deployment workflow is `.github/workflows/deploy-azure.yml` and the Azure Infrastructure as Code is under `infra/azure/`.

## Production topology

```text
GitHub protected production environment
        │
        ▼
GitHub Actions OIDC → Azure
        │
        ├─ compile/validate Bicep before deployment authority
        ├─ build immutable image
        ├─ push commit-SHA image to ACR
        ├─ run Alembic migration job
        ├─ deploy Container App
        └─ deploy operational controls / readiness checks

Internet
   │
   ▼
https://simulator.etisframework.org
   │
Azure Container Apps
   │  user-assigned managed identity
   ├────────────► Azure Key Vault
   ├────────────► Azure Container Registry
   │
   ▼
Private VNet integration
   │
   ▼
Azure Database for PostgreSQL Flexible Server

Application Insights → Log Analytics → Azure Monitor alerts/action group
```

## Infrastructure layers

### `infra/azure/main.bicep`

Creates the durable foundation:

- VNet/subnets;
- PostgreSQL delegated subnet;
- private PostgreSQL DNS zone/link;
- Log Analytics;
- workspace-based Application Insights;
- ACR;
- user-assigned runtime managed identity;
- Key Vault and role assignments;
- Container Apps environment;
- PostgreSQL Flexible Server/database.

### `infra/azure/secrets.bicep`

Creates/updates Key Vault runtime secrets from protected deployment inputs:

- database URL;
- ETIS session secret;
- Entra client secret;
- GitHub App private key;
- GitHub OAuth client secret;
- OpenAI API key.

Secrets must never be committed to source control.

### `infra/azure/migration.bicep`

Defines the Container Apps migration job that runs `alembic upgrade head` using the immutable production image and Key Vault-backed database URL.

Production application startup does not own schema migration.

### `infra/azure/app.bicep`

Defines the production Container App:

- HTTPS ingress;
- custom domain/certificate binding;
- managed identity;
- ACR image pull;
- Key Vault-backed Container App secrets;
- production Entra/GitHub/OpenAI configuration;
- health/readiness probes;
- bounded horizontal scaling.

### `infra/azure/operations.bicep`

Defines the production action group and Azure Monitor alerts for:

- Container App restarts;
- HTTP 5xx;
- PostgreSQL availability;
- PostgreSQL storage percentage.

## Production resource names

Accepted live resources include:

- resource group: `etis-studio-prod`;
- Container App: `etis-studio-prod`;
- ACR: `etisstudioprodev3bgd5nmvfg4`;
- PostgreSQL: `etis-studio-prod-pg-ev3bgd5nmvfg4`;
- Key Vault: `etis-studio-prod-kv-ev3b`;
- managed identity: `etis-studio-prod-runtime`;
- Application Insights: `etis-studio-prod-appi`;
- Log Analytics: `etis-studio-prod-law`;
- custom hostname: `simulator.etisframework.org`.

Resource suffixes are deployment-specific. Do not hard-code subscription IDs or credentials into documentation/scripts when resource discovery can be used instead.

## Production configuration requirements

Production `Settings` fail closed when required values are missing or unsafe.

Required production families include:

- `ETIS_ENV=production`;
- PostgreSQL `ETIS_DATABASE_URL`;
- sufficiently strong `ETIS_SESSION_SECRET`;
- HTTPS `ETIS_WEB_ORIGIN`;
- `ETIS_DEV_LOGIN=false`;
- explicit `ENTRA_TENANT` UUID;
- Entra client ID/secret/redirect URI;
- GitHub OAuth client ID/secret/redirect URI;
- GitHub App ID/private key/slug;
- OpenAI key when AI is enabled.

The protected deployment workflow must validate `ETIS_GITHUB_APP_SLUG` and pass it to Bicep/runtime configuration. CI and the manual release-gate production-container smoke also provide `GITHUB_APP_SLUG`.

## Microsoft Entra configuration

Production identity rules:

- institutional users authenticate with Microsoft Entra;
- normal allowed domain is `luc.edu`;
- production uses an explicit tenant UUID rather than a broad organizations/common tenant selector;
- Studio stores no user password;
- course authorization is database-derived after authentication.

The controlled external production-test student is an exact configured identity exception. It must not become a general Gmail-domain allowance.

## GitHub OAuth configuration

GitHub OAuth is used to link the individual Studio user to a GitHub identity.

Security requirements:

- callback is bound to the initiating Studio session/user;
- OAuth state alone is not sufficient to mutate identity;
- no GitHub OAuth access token is retained;
- OAuth scope remains no broader than required for public identity information.

## GitHub App configuration

The ETIS Engineering Studio GitHub App is used for repository evidence access.

Required registration/configuration:

- App is installable beyond the owning organization because approved personal repositories are supported;
- repository permissions remain read-only/minimal for evidence acquisition;
- installation must be **Only select repositories**;
- ETIS rejects `all repositories` scope;
- owner-targeted installation navigation uses the resolved immutable repository-owner GitHub account ID;
- personal repository authorization is performed by the actual owner;
- organization authorization/request follows GitHub's organization owner/admin authority model.

Production GitHub App completion configuration:

- **Setup URL:** `https://simulator.etisframework.org/github/setup-complete`
- **Redirect on update:** enabled

The Setup URL improves return-to-Studio UX. It is **not** the repository verification boundary. The student still performs Step 2 exact-repository verification in Studio.

## Repository verification boundary

The candidate repository is never promoted solely because authorization was opened or because GitHub returned from an installation page.

Verification must:

1. re-read/lock current candidate state;
2. confirm the candidate has not changed during external checks;
3. confirm installation repository selection is not `all`;
4. confirm the exact nominated repository is accessible;
5. obtain an installation token restricted to that exact repository;
6. promote only the current candidate to verified team state.

## Managed identity and Key Vault

Production runtime uses user-assigned identity `etis-studio-prod-runtime`.

Accepted Key Vault authority:

- role: `Key Vault Secrets User`;
- scope: production Key Vault only.

Container App secrets are Key Vault references and runtime environment variables consume them by `secretRef`.

## Private PostgreSQL boundary

PostgreSQL production access is private-only through VNet integration, delegated subnet, and private DNS. Public network access is disabled.

Accepted baseline:

- PostgreSQL 16;
- `Standard_B1ms` Burstable;
- 32 GB;
- 7-day backup retention;
- geo-redundant backup disabled;
- HA disabled.

A live PITR restore drill passed during acceptance; see `operations/DATABASE_RECOVERY_RUNBOOK.md`.

## Deployment sequence

The protected manual workflow follows this control intent:

```text
select commit
  → release gate
      → install pinned Bicep CLI
      → compile IaC
      → production-container smoke
      → validation/tests
  → acquire Azure deployment authority
  → foundation/secrets as required
  → build/push immutable commit-SHA image
  → migration
  → application
  → operational controls
  → readiness verification
```

Do not obtain/use Azure deployment authority before the selected commit passes the release gate.

## Scaling

Accepted live runtime after production acceptance:

- `minReplicas=1`;
- `maxReplicas=5`.

The minimum was changed from zero to one after intermittent long reloads were observed during acceptance, preventing normal scale-to-zero cold starts.

**Important drift:** source `infra/azure/app.bicep` still defaults `minReplicas` to `0`. A future deployment may therefore revert production to scale-to-zero unless the source/default or deployment parameter is reconciled. This is a known follow-up item in `NEXT_BUILD.md`.

## Observability

Accepted live monitoring:

- workspace-based Application Insights;
- Log Analytics retention: 30 days;
- operations action group with enabled email receiver;
- HTTP 5xx alert;
- container restart alert;
- PostgreSQL not-alive alert;
- PostgreSQL storage alert.

## Cost controls

Accepted production resource-group budget:

- `$100/month`;
- 50% actual-cost notification;
- 80% actual-cost notification;
- 100% actual-cost notification.

Budget alerts do not automatically stop production resources.

## Rollback

Container Apps is configured in Single revision mode. Accepted rollback posture is to redeploy a prior immutable commit-SHA image from ACR.

Multiple prior SHA tags were verified present during production acceptance. A destructive rollback drill was not performed solely to prove a mechanism already supported by retained immutable images.

## Post-deployment verification

Every production-changing deployment should verify at minimum:

- Container App latest revision becomes ready;
- `/health` returns 200;
- `/ready` returns 200 with database connected and migration current;
- expected identity/repository integration affected by the release;
- no new alert/telemetry anomaly;
- production user journey relevant to the change.

Production acceptance evidence is recorded in `operations/POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md` and `PRODUCTION_BASELINE.md`.
