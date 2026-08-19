# ETIS Engineering Studio Azure Infrastructure

This directory contains the source-controlled Azure Infrastructure as Code for
the ETIS Engineering Studio production environment.

The infrastructure is divided into explicit deployment layers so that
foundation resources, secrets, database migration, application deployment, and
operational controls can be reconciled independently and in a controlled order.

## Files

### `main.bicep`

Creates the long-lived Azure production foundation:

- Azure Virtual Network;
- Container Apps infrastructure subnet;
- delegated PostgreSQL subnet;
- PostgreSQL private DNS zone and VNet link;
- Log Analytics workspace;
- workspace-based Application Insights;
- Azure Container Registry;
- user-assigned runtime managed identity;
- Azure Key Vault;
- managed-identity role assignments for ACR and Key Vault;
- Azure Container Apps managed environment;
- Azure Database for PostgreSQL Flexible Server;
- ETIS PostgreSQL database.

PostgreSQL is deployed through private VNet integration rather than a public
database-access model.

### `secrets.bicep`

Provisions production runtime secrets into Azure Key Vault from secure
deployment parameters.

It manages:

- ETIS PostgreSQL SQLAlchemy connection URL;
- ETIS session signing secret;
- Microsoft Entra client secret;
- GitHub App private key;
- GitHub OAuth client secret;
- OpenAI API key.

Secret values must never be committed to this repository.

### `migration.bicep`

Creates the manual Azure Container Apps migration job.

The job:

- runs the immutable production application image;
- uses the runtime managed identity;
- pulls from private ACR without registry credentials;
- obtains the database URL from Key Vault;
- runs `alembic upgrade head`;
- executes inside the Container Apps environment so it can reach private
  PostgreSQL.

A successful production migration is required before application deployment.

### `app.bicep`

Deploys the ETIS Engineering Studio production Container App.

It defines:

- public HTTPS application ingress;
- user-assigned managed identity;
- private ACR image pull;
- Key Vault-backed runtime secrets;
- fail-closed production configuration;
- Microsoft Entra configuration;
- GitHub App and GitHub OAuth configuration;
- OpenAI configuration;
- `/health` liveness probe;
- `/ready` readiness probe;
- bounded horizontal scaling.

The application may scale to zero when idle.

### `operations.bicep`

Creates the initial Azure Monitor operational controls:

- production operations action group;
- Container App `RestartCount` alert;
- Container App HTTP `5xx` alert;
- PostgreSQL `is_db_alive` alert;
- PostgreSQL `storage_percent` alert.

These alerts are intentionally compatible with application scale-to-zero
behavior.

## Deployment order

The authorized production deployment workflow is:

`release validation -> foundation -> secrets -> immutable image -> migration -> application -> operational controls -> readiness verification`

The implementation lives in:

`.github/workflows/deploy-azure.yml`

The deployment workflow is manually triggered and protected by the GitHub
`production` environment.

Azure authority is acquired only after the selected commit passes the release
gate.

## CI validation

GitHub CI validates the Azure infrastructure without requiring Azure
credentials.

CI:

- installs a pinned Bicep CLI;
- compiles all Bicep templates;
- validates production database migrations;
- performs a PostgreSQL logical backup/restore drill;
- builds the production container;
- smoke-tests `/ready`;
- runs the complete Python regression suite.

Successful Bicep compilation proves template syntax and type checking. It does
not prove live Azure region availability, quota, alert delivery, networking, or
point-in-time recovery.

## Identity and secret boundaries

Application runtime authority is separate from GitHub deployment authority.

The application and migration job use a user-assigned managed identity with only
the Azure roles required for:

- ACR image pull;
- Key Vault secret access.

ACR administrative credentials remain disabled.

Runtime secrets remain in Azure Key Vault and are referenced by Container Apps
rather than stored as literal environment values.

## Database boundary

Azure Database for PostgreSQL Flexible Server is the durable application store.

The production database is VNet-integrated through its delegated subnet and
private DNS configuration.

Production schema lifecycle is owned by Alembic.

Application startup does not silently create or migrate the production schema.

## Operational readiness

Gate 16 operational procedures are documented under:

`docs/operations/`

Those procedures cover:

- monitoring;
- health/readiness interpretation;
- incident response;
- credential incidents;
- database recovery;
- point-in-time restore;
- RTO/RPO planning;
- recovery evidence;
- post-provisioning verification.

Some operational controls can be proven before Azure provisioning; others
require live post-provisioning evidence.

In particular, live Azure point-in-time restore, alert delivery, telemetry
ingestion, and restored-server networking must be verified after production
resources exist and before student production access is approved.

## Production boundary

These templates define the intended production infrastructure, but source code
alone does not authorize deployment or student use.

Before production Azure provisioning begins, the project still requires:

- protected GitHub production-environment configuration;
- Azure OIDC configuration;
- production secret values at the deployment boundary;
- the intended production hostname and DNS plan;
- Microsoft Entra callback configuration;
- GitHub App/OAuth configuration;
- explicit **Gate 17 — Final Pre-Azure Go/No-Go** approval.

A Gate 17 GO authorizes provisioning and deployment only.

After provisioning and before student production access, the project still
requires:

- final hostname, DNS, HTTPS, and callback validation;
- live Azure operational validation;
- Gate 16 post-provisioning evidence;
- live point-in-time recovery validation;
- production authentication and authorization validation;
- explicit **Post-Provisioning Production Acceptance** GO.

No infrastructure requirement should be weakened merely to simplify local
development or initial deployment.
