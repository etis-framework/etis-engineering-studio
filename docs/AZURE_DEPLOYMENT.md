# Azure Deployment Plan

## Purpose

This document defines the production deployment architecture and reproducible
Infrastructure as Code (IaC) sequence for the ETIS Engineering Studio.

The production deployment is intentionally small for the initial COMP330-F26
course population, but it is designed to preserve the security, durability,
identity, migration, observability, and multi-replica guarantees established by
the pre-Azure production-hardening gates.

Azure deployment is performed through the manually triggered GitHub Actions
workflow in `.github/workflows/deploy-azure.yml`. The workflow revalidates the
selected Git commit before acquiring Azure authority and then deploys the exact
validated commit.

No production deployment should bypass that release gate.

## Production topology

The initial production topology consists of:

- **Azure Container Apps** for the FastAPI application and bundled browser UI.
- **Azure Container Apps Job** for explicit Alembic database migration execution.
- **Azure Database for PostgreSQL Flexible Server** for durable application state.
- **Azure Container Registry (ACR)** for immutable application images.
- **Azure Key Vault** for runtime secrets.
- **User-assigned managed identity** for application and migration-job access to
  ACR and Key Vault.
- **Azure Virtual Network** with separate Container Apps and PostgreSQL subnets.
- **Private DNS** for PostgreSQL Flexible Server.
- **Log Analytics** for centralized operational logging.
- **Application Insights** backed by the Log Analytics workspace.

The Studio application has public HTTPS ingress. PostgreSQL does not require a
public Internet database endpoint: the database is reached from the Container
Apps environment through the private VNet-integrated PostgreSQL network path.

This topology deliberately avoids Kubernetes and unnecessary microservices. The
initial course population does not justify that operational complexity.

## Infrastructure layers

Azure infrastructure is split into four declarative Bicep layers.

### 1. Foundation — `infra/azure/main.bicep`

The foundation creates the long-lived Azure infrastructure:

- virtual network;
- Container Apps infrastructure subnet;
- delegated PostgreSQL subnet;
- PostgreSQL private DNS zone and VNet link;
- Log Analytics workspace;
- Application Insights;
- Azure Container Registry;
- user-assigned runtime managed identity;
- Azure Key Vault;
- ACR `AcrPull` authorization for the runtime identity;
- Key Vault `Key Vault Secrets User` authorization for the runtime identity;
- Container Apps managed environment;
- PostgreSQL Flexible Server;
- application PostgreSQL database.

The foundation does **not** deploy the ETIS application container. This allows a
new environment to be created before the first ETIS application image exists.

### 2. Runtime secrets — `infra/azure/secrets.bicep`

Runtime secrets are provisioned into Azure Key Vault from secure deployment
parameters.

The secret layer provisions:

- PostgreSQL SQLAlchemy database URL;
- ETIS session signing secret;
- Microsoft Entra client secret;
- GitHub App private key;
- GitHub OAuth client secret;
- OpenAI API key.

The PostgreSQL URL is constructed for the private Flexible Server endpoint and
requires TLS.

Secret values must never be committed to the repository, embedded in Bicep
source, emitted in application logs, or passed as literal Container App
environment values.

### 3. Database migration — `infra/azure/migration.bicep`

Database schema migration runs as a manually triggered Azure Container Apps Job.

The migration job:

- runs the exact immutable application image selected for deployment;
- uses the production user-assigned managed identity;
- pulls the image from private ACR without registry username/password credentials;
- obtains `ETIS_DATABASE_URL` through an Azure Key Vault secret reference;
- executes `alembic upgrade head`;
- runs inside the Container Apps environment so it can reach the private
  PostgreSQL Flexible Server;
- must succeed before the production application deployment proceeds.

GitHub-hosted runners therefore do not require direct network access to the
production database.

### 4. Application — `infra/azure/app.bicep`

The application layer deploys the ETIS Engineering Studio Container App.

The application:

- uses the same immutable image that passed the release gate and migration;
- uses user-assigned managed identity for private ACR image pull;
- uses Key Vault-backed Container Apps secret references;
- runs with `ETIS_ENV=production`;
- runs with `ETIS_DEV_LOGIN=false`;
- receives the canonical HTTPS web origin;
- receives explicit Microsoft Entra tenant and application configuration;
- receives GitHub App and GitHub OAuth configuration;
- receives OpenAI configuration;
- exposes HTTPS ingress on the Studio application;
- uses `/health` for liveness;
- uses `/ready` for readiness;
- permits bounded horizontal replica scaling.

The application is not considered successfully deployed merely because a
Container App revision starts. The deployment workflow verifies `/ready` and
requires the service to report both application readiness and a current database
migration state.

## Managed identity and authorization

The production application and migration job use a user-assigned managed
identity.

The identity is created in the foundation layer before either workload exists.
This avoids an initial-deployment dependency on a system-assigned identity that
would not exist until after the Container App was created.

The runtime identity receives only the Azure permissions required for its
runtime responsibilities:

- **AcrPull** on the ETIS Azure Container Registry;
- **Key Vault Secrets User** on the ETIS production Key Vault.

ACR administrative credentials remain disabled.

No Docker registry username or password is configured in the Container App or
migration job.

GitHub Actions deployment authority is separate from application runtime
authority.

## Private database boundary

PostgreSQL Flexible Server is deployed through its delegated VNet subnet and
associated private DNS zone.

The architecture intentionally does not create PostgreSQL firewall rules that
permit general Internet connectivity.

Application and migration workloads reach PostgreSQL from the Container Apps
environment across the Azure virtual network.

The public application boundary and private database boundary are therefore
separate:

- the Studio is reachable by authorized users over HTTPS;
- PostgreSQL is not intended to be directly reachable by students, browsers, or
  GitHub-hosted CI runners.

## Production configuration

The production deployment must satisfy the application's fail-closed
configuration contract.

Required production configuration includes at least:

- `ETIS_ENV=production`
- `ETIS_DEV_LOGIN=false`
- `ETIS_WEB_ORIGIN`
- `ETIS_DATABASE_URL`
- `ETIS_SESSION_SECRET`
- `ETIS_COURSE_NAMESPACE`
- Microsoft Entra client ID, client secret, redirect URI, and explicit tenant UUID
- GitHub App ID and private key
- GitHub OAuth client ID, client secret, and redirect URI
- OpenAI API key when AI functionality is enabled

The production session secret must meet the application's minimum strength
requirement.

The production web origin must use HTTPS.

The Microsoft Entra tenant must be explicitly configured rather than using the
development `organizations` default.

## GitHub Actions deployment sequence

Production deployment is manual and runs through
`.github/workflows/deploy-azure.yml`.

The required sequence is:

1. **Release gate**
   - check out the selected Git commit;
   - install locked development dependencies;
   - audit production Python dependencies;
   - validate PostgreSQL/Alembic migration correctness;
   - build the production container;
   - smoke-test that container in production mode;
   - run the complete backend regression suite;
   - validate the COMP 330 course model.

2. **Acquire Azure authority**
   - only after the release gate succeeds;
   - authenticate using GitHub Actions OIDC rather than a long-lived Azure
     deployment password.

3. **Reconcile foundation infrastructure**
   - deploy `infra/azure/main.bicep`.

4. **Provision Key Vault runtime secrets**
   - deploy `infra/azure/secrets.bicep` using GitHub environment secrets as secure
     deployment inputs.

5. **Build and push the immutable production image**
   - authenticate to ACR;
   - build from the already validated commit;
   - tag the image with the Git commit SHA;
   - push that immutable deployment candidate to ACR.

6. **Reconcile the migration job**
   - deploy `infra/azure/migration.bicep` using the immutable SHA image.

7. **Execute the production migration**
   - start the Container Apps migration job;
   - wait for the exact execution to finish;
   - require successful completion;
   - stop deployment on migration failure or timeout.

8. **Deploy the application**
   - deploy `infra/azure/app.bicep` using the same immutable SHA image.

9. **Verify production readiness**
   - request the deployed `/ready` endpoint;
   - require `"status":"ready"`;
   - require `"migration_current":true`;
   - fail the deployment if production does not become ready.

The deployment order is intentionally:

`release validation -> infrastructure -> secrets -> image -> migration -> application -> readiness verification`

## GitHub production environment configuration

The GitHub `production` environment is the deployment-control boundary for
production-specific variables and secrets.

Expected GitHub environment configuration includes the Azure OIDC identifiers,
resource-group/location settings, application identity/provider settings, and
secure values consumed by the Key Vault provisioning deployment.

Exact production values are established during the controlled Azure deployment
preparation process. They must not be added to source control.

The GitHub production environment should use appropriate repository/environment
protection settings before student rollout.

## Initial capacity posture

The initial deployment is optimized for approximately 30 students and modest
classroom concurrency.

The application defaults to bounded Container Apps scaling rather than a fixed
large fleet.

PostgreSQL begins with a modest Burstable SKU and parameterized storage and
backup retention settings.

Infrastructure parameters permit these choices to be increased later without
changing application architecture.

Sizing must be reviewed against actual Azure region availability, observed
course demand, and current Azure pricing before production rollout.

## Cost controls

Wave 1 should avoid always-on resources that do not contribute student value.

Before student access is enabled:

- establish an Azure budget;
- configure appropriate cost notifications;
- verify expected Container Apps scaling;
- verify PostgreSQL SKU and storage;
- verify Log Analytics/Application Insights ingestion posture;
- verify OpenAI usage controls separately at the application/provider boundary.

Exact pricing is intentionally not frozen in source because Azure pricing and
regional SKU availability change.

## Secrets and credential handling

Production secrets belong in Azure Key Vault.

They must not appear in:

- repository source;
- committed parameter files;
- application logs;
- evidence snapshots;
- AI prompts;
- browser-delivered configuration;
- Docker registry credentials.

GitHub Actions receives deployment-time secure values from the protected GitHub
production environment and provisions them into Key Vault.

The application subsequently consumes Key Vault references using managed
identity.

## Database durability and migration policy

PostgreSQL Flexible Server automatic backups provide the database durability
foundation.

Schema changes are applied explicitly through Alembic before application
deployment.

Application startup is not responsible for silently migrating the production
database.

A failed migration prevents the new application deployment from proceeding.

Operational backup validation, point-in-time restore testing, disaster recovery,
and recovery runbooks are Gate 16 responsibilities.

## Observability boundary

The foundation creates Log Analytics and workspace-based Application Insights.

Telemetry must preserve the security and privacy requirements defined in
`docs/SECURITY_AND_PRIVACY.md`, including sensitive-data-safe logging.

Gate 15 establishes the Azure observability infrastructure.

Gate 16 owns operational alert definitions, dashboards, production monitoring
procedures, incident handling, backup/restore exercises, and recovery
verification.

## DNS and production hostname

The Container App provides an Azure-managed HTTPS hostname at initial
deployment.

The intended production experience may later use the ETIS custom hostname.

Custom DNS, certificate validation, OAuth callback registration, and final
production hostname verification must be completed before student access is
enabled.

The canonical `ETIS_WEB_ORIGIN`, Microsoft Entra callback URI, and GitHub OAuth
callback URI must agree with the hostname actually presented to users.

## Controlled rollout sequence

**Gate 17 — Final Pre-Azure Go/No-Go must reach an explicit GO before any
production Azure resources are provisioned or the production deployment
workflow is authorized.**

After Gate 17 GO and after the infrastructure and application have been
successfully deployed:

1. verify production readiness;
2. configure/verify the final HTTPS hostname;
3. configure Microsoft Entra production callback settings;
4. configure/install the read-only GitHub App on authorized repositories;
5. configure GitHub OAuth;
6. import the COMP330-F26 roster and team mappings;
7. test instructor and student authorization;
8. test at least one authorized private repository;
9. perform the required Gate 16 live operational and recovery validation;
10. complete the post-provisioning **Production Acceptance** review;
11. enable student access only after Production Acceptance reaches an explicit
    GO and all production controls pass.

## Gate boundaries

Gate 15 establishes reproducible Azure infrastructure and the controlled
deployment path.

It does **not** itself authorize student production use.

The following remain later-stage responsibilities:

- operational alerts and escalation;
- backup/restore testing;
- recovery exercises;
- incident runbooks;
- final production configuration verification;
- Gate 17 pre-Azure deployment authorization;
- final DNS/callback validation after provisioning;
- live Gate 16 operational/recovery evidence;
- post-provisioning Production Acceptance before student access.

No production-control requirement should be weakened merely to simplify local
development or initial Azure provisioning.
