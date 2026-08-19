# Gate 17 — Final Pre-Azure Go/No-Go

## 1. Purpose

Gate 17 is the **Final Pre-Azure Go/No-Go** for the ETIS Engineering Studio
v0.16.0 production-integration effort.

Its purpose is to decide whether the project is sufficiently complete,
controlled, reviewed, and configured to begin production Azure provisioning.

An explicit Gate 17 **GO authorizes provisioning** and use of the controlled
production deployment workflow.

A Gate 17 GO **does not authorize student access**.

Student production access requires a separate **Post-Provisioning Production
Acceptance** review after the live Azure environment exists and all required
live controls have been verified.

At the time this Gate 17 artifact was established:

- all prior gates have completed their source-controlled implementation and
  required CI validation;
- the current branch remains the controlled v0.16.0 production-hardening
  branch;
- the production deployment workflow remains manual;
- no Azure resources have been provisioned;
- live Azure controls are not yet verified.

Gate 17 must never convert an untested live-production assumption into evidence.

---

## 2. Decision outcomes

Gate 17 has exactly two decision outcomes.

### GO

GO means:

- all blocking pre-Azure requirements are satisfied;
- required operator-configured controls have been independently verified;
- the production security review is complete;
- there are no unresolved blockers that make provisioning unsafe;
- any accepted deferral is explicit, bounded, owned, and does not weaken a
  required production security or authorization control;
- the selected Git commit has passed the controlled release and CI evidence;
- the project is authorized to begin Azure provisioning.

GO does not mean that the Studio is ready for students.

### NO-GO

NO-GO means Azure provisioning is not authorized.

A NO-GO is required when any blocking pre-Azure control is:

- missing;
- unverifiable;
- materially inconsistent;
- insecure;
- dependent on an unresolved production decision;
- configured outside the documented authority boundary;
- or deferred without explicit acceptance and ownership.

---

## 3. Evidence classification

Every Gate 17 control must be classified as exactly one of:

- **Proven** — established directly by source-controlled implementation and
  reviewable evidence.
- **Verified in CI** — exercised by repeatable automated validation.
- **Operator-configured** — requires an authorized operator to verify an
  external configuration that cannot be proven from repository source alone.
- **Requires post-provisioning validation** — can only be tested after Azure
  resources exist.
- **Blocked** — prevents Gate 17 GO.
- **Deferred with explicit acceptance** — intentionally postponed with a
  documented owner, rationale, risk boundary, and later acceptance point.

Each evidence entry must identify:

- control;
- classification;
- owner;
- evidence reference;
- rationale;
- result;
- follow-up, if any.

A classification of Operator-configured is not itself a pass. The actual
configuration must be inspected and recorded before Gate 17 GO.

---

## 4. Source-controlled and CI evidence

The following pre-Azure evidence is already established through prior gates and
the current CI pipeline.

### 4.1 Application and security foundation

Evidence includes:

- hardened database-backed sessions;
- secure cookies;
- CSRF protection;
- current database-derived authorization;
- fail-closed privileged access;
- scoped GitHub App repository access;
- immutable frozen evidence semantics;
- fail-closed AI/provider boundaries;
- bounded security headers and HTTPS-origin requirements;
- production configuration validation;
- PostgreSQL/Alembic migration discipline;
- multi-replica concurrency and idempotency controls;
- supply-chain validation;
- production container build and smoke testing.

Classification: **Proven / Verified in CI**.

### 4.2 Production infrastructure as code

Evidence includes:

- private PostgreSQL networking;
- Container Apps environment;
- Azure Container Registry with admin access disabled;
- user-assigned managed identity;
- Key Vault;
- Log Analytics;
- Application Insights;
- migration job;
- production application definition;
- operational alert definitions;
- managed-identity access to ACR and Key Vault.

Classification: **Proven / Verified in CI**.

Bicep compilation proves that the templates compile. It does not prove that
live Azure resources behave correctly.

### 4.3 Recovery preparation

Evidence includes:

- production operations runbook;
- incident-response runbook;
- database-recovery runbook;
- PostgreSQL logical backup/restore drill in CI;
- restored Alembic revision verification;
- restored sentinel-data verification.

Classification: **Proven / Verified in CI**.

Live Azure point-in-time recovery remains **Requires post-provisioning
validation**.

---

## 5. Wave 1 pre-Azure evidence

The Wave 1 acceptance criteria include both pre-Azure software behavior and
live production controls.

The following criteria have pre-Azure automated evidence:

- **A1** and **A2** machine-readable phase contracts;
- A1/A2 scenario configuration;
- student/team authorization boundaries;
- frozen evidence snapshots;
- consequence-oriented evidence challenges;
- evidence provenance;
- instructor visibility into review activity;
- peer/privacy boundaries;
- automated tests;
- deterministic operation when **AI can be disabled**;
- representative **strong**, **mixed**, and **weak** repository profiles
  exercised against A1 and A2;
- immutable frozen evidence and correction semantics.

These source-controlled criteria may be classified Proven or Verified in CI.

The Azure-backed portions of Wave 1 acceptance remain subject to
Post-Provisioning Production Acceptance.

---

## 6. Required production security review

The production security review is a **blocking Gate 17 requirement**.

The review must verify, at minimum:

- production sessions fail closed;
- current authorization is database-derived;
- CSRF protection remains enforced;
- secure-cookie behavior is appropriate for production;
- permitted origins and HTTPS enforcement are correct;
- production repository access uses the GitHub App and not a PAT;
- GitHub App permissions remain least-privilege and read-only where intended;
- secrets are excluded from repository source and browser-delivered
  configuration;
- Key Vault is the intended runtime secret boundary;
- AI/provider failures do not become fabricated evidence or fabricated
  reviewer conversation;
- application and AI rate/cost controls remain bounded;
- logging remains sensitive-data-safe;
- backup and recovery procedures are defined;
- production authentication and authorization boundaries remain fail closed.

Classification: **Blocking until completed and recorded**.

Owner: authorized production/security reviewer.

---

## 7. GitHub production environment

The GitHub **production environment** is the deployment-control boundary.

Before Gate 17 GO, an authorized operator must verify:

- the environment exists;
- environment protection is enabled;
- appropriate required reviewer or equivalent approval protection is
  configured;
- only the intended deployment workflow uses the production environment;
- secrets and variables are scoped to the production environment rather than
  committed to source;
- deployment cannot bypass the release-validation job.

Classification: **Operator-configured / Blocking until verified**.

---

## 8. Azure OIDC and federated deployment identity

The production deployment uses **Azure OIDC** and federated identity rather
than a long-lived Azure deployment password.

Before Gate 17 GO, verify:

- the intended Azure application/service principal exists;
- the GitHub Actions **federated** credential matches the repository,
  production environment, and intended subject;
- the credential grants no broader authority than required;
- `AZURE_CLIENT_ID` is present in the protected GitHub production environment;
- `AZURE_TENANT_ID` is present;
- `AZURE_SUBSCRIPTION_ID` is present;
- the target subscription is the intended ETIS production subscription;
- the target resource group and Azure location are approved.

### Azure bootstrap boundary

Gate 17 deliberately separates creation of the deployment trust from creation
of production Azure resources.

Before Gate 17 GO:

- the dedicated Microsoft Entra deployment application exists;
- the GitHub Actions federated credential is bound to the intended repository
  and `production` environment;
- the protected GitHub production environment contains the required Azure OIDC
  identifiers;
- **no production Azure resource group is created before Gate 17 GO**;
- the GitHub deployment principal has **zero Azure resource authority before
  Gate 17 GO**.

This allows the identity and trust relationship to be reviewed without
prematurely provisioning production infrastructure or granting deployment
authority.

**After Gate 17 GO**, the controlled Azure bootstrap sequence is:

1. **Create the empty production resource group** using the approved
   `AZURE_RESOURCE_GROUP` and `AZURE_LOCATION`.
2. Assign the dedicated GitHub deployment principal, at **resource-group
   scope**, the minimum roles required by the validated deployment:
   - **Contributor** for resource creation and management;
   - **Role Based Access Control Administrator** because the foundation Bicep
     creates bounded runtime role assignments;
   - **AcrPush** so the validated immutable container image can be pushed to
     the production Azure Container Registry.
3. Confirm there is **no subscription-wide deployment role** for the GitHub
   deployment principal.
4. **Then run the production deployment workflow** from the protected GitHub
   `production` environment.

These post-GO bootstrap actions authorize deployment only. They do not
constitute Post-Provisioning Production Acceptance and do not authorize student
access.

Classification: **Operator-configured / Blocking until verified**.

---

## 9. Required deployment variables and secrets

Gate 17 must verify the presence and intended ownership of the production
configuration required by `.github/workflows/deploy-azure.yml`.

### Azure/deployment configuration

Required configuration includes:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `ETIS_WEB_ORIGIN`
- `OPERATIONS_ALERT_EMAIL`

- `ETIS_GITHUB_APP_ID`

- `ETIS_GITHUB_APP_SLUG`

- `ETIS_GITHUB_OAUTH_CLIENT_ID`


### Sensitive values

Required protected values include:

- `POSTGRES_ADMIN_PASSWORD`
- `ETIS_SESSION_SECRET`
- `ENTRA_CLIENT_SECRET`
- `ETIS_GITHUB_APP_PRIVATE_KEY`
- `ETIS_GITHUB_OAUTH_CLIENT_SECRET`
- `OPENAI_API_KEY`

Do not record secret values.

Gate 17 evidence should record only that each required value:

- exists;
- is scoped correctly;
- has an identified owner;
- is intended for this production environment;
- and is not present in source control.

Do not place an access token, database password, API key, session cookie, OAuth
secret, private key, or equivalent credential into the Gate 17 evidence record.

Classification: **Operator-configured / Blocking until verified**.

---

## 9A. Production-test student configuration

Gate 17 must verify the bounded Production Acceptance student configuration
before Azure provisioning is authorized.

Required operator-configured values are:

- `ETIS_PRODUCTION_TEST_STUDENT_OID`
- `ETIS_PRODUCTION_TEST_STUDENT_EMAIL`
- `ETIS_PRODUCTION_TEST_STUDENT_ID`
- `ETIS_PRODUCTION_TEST_SECTION_KEY`
- `ETIS_PRODUCTION_TEST_TEAM_KEY`

The configured principal must be bound by its **exact Entra Object ID**.

The configured student may only be enrolled in the **designated
production-test section** and assigned to the **designated production-test
team**. It receives ordinary student authority only.

The exception **does not allow gmail.com generally** and must not broaden
`ENTRA_ALLOWED_DOMAIN` or create a general external-user authorization path.

Gate 17 evidence records only the presence, ownership, and intended scope of
these settings. The actual private Object ID and email need not be copied into
the evidence record.

Classification: **Operator-configured / Blocking until verified**.

## 10. Microsoft Entra configuration

Before Gate 17 GO, verify the intended Microsoft Entra production identity
configuration:

- `ENTRA_CLIENT_ID`;
- tenant authority;
- intended Loyola identity boundary;
- production redirect/callback plan;
- least-privilege application configuration;
- operator ownership.

The final live callback must be verified after the production hostname exists.

Pre-Azure classification: **Operator-configured**.

Live callback behavior: **Requires post-provisioning validation**.

---

## 11. GitHub App and GitHub OAuth

Before Gate 17 GO, verify the intended production:

- GitHub App identity;
- GitHub App ID;
- GitHub App slug where used;
- private-key secret presence;
- least-privilege repository permissions;
- installation model for authorized private team repositories;
- GitHub OAuth client ID;
- GitHub OAuth client-secret presence;
- callback plan aligned with the intended hostname.

The final GitHub App installation and live GitHub OAuth callback behavior are
verified after provisioning.

Pre-Azure classification: **Operator-configured**.

Live repository and OAuth behavior: **Requires post-provisioning validation**.

---

## 12. OpenAI production configuration

Before Gate 17 GO, verify:

- the production OpenAI account/project boundary;
- `OPENAI_API_KEY` secret presence;
- intended model configuration;
- bounded application usage behavior;
- expected cost/usage oversight;
- human ownership of model configuration.

The Studio must continue to fail closed when required semantic coaching is not
available.

Classification: **Operator-configured / Blocking until verified**.

---

## 13. Production hostname and callback plan

Before Gate 17 GO, the intended production **hostname** must be selected and
documented.

The plan must establish:

- intended `ETIS_WEB_ORIGIN`;
- HTTPS-only production use;
- intended DNS ownership;
- Microsoft Entra callback path;
- GitHub OAuth callback path;
- consistency between the origin and callback configuration.

Final DNS, certificate, HTTPS, and callback verification cannot occur until the
live application exists.

Pre-Azure classification: **Operator-configured**.

Final verification: **Requires post-provisioning validation**.

---

## 14. Azure budget and cost controls

A production **budget** and **cost notification** posture must be defined before
Gate 17 GO.

The authorized operator must verify:

- intended Azure subscription;
- initial cost expectations;
- budget amount or approved cost-control threshold;
- cost-notification recipients;
- expected PostgreSQL SKU;
- expected Container Apps scaling posture;
- expected telemetry-ingestion posture;
- OpenAI usage/cost monitoring boundary.

Where Azure requires the live resource or subscription configuration to create
a specific control, Gate 17 must record the approved configuration plan and
owner, and Production Acceptance must verify the live control.

Classification: **Operator-configured / Blocking until the approved posture is
recorded**.

Live budget/alert behavior where applicable: **Requires post-provisioning
validation**.

---

## 15. Retention policy boundary

Security and privacy policy requires the responsible course/institutional
authority to define retention periods for production operation.

Gate 17 must record the status and owner of retention decisions for:

- engineering records;
- student identity and attribution data;
- archived course-administration records;
- authentication/session records;
- operational telemetry;
- backups;
- externally processed data where configurable.

A missing retention decision must not be silently replaced with an arbitrary
application default.

If a retention decision can responsibly be finalized during production setup,
it must be classified **Deferred with explicit acceptance**, with owner,
rationale, and completion point recorded.

Any retention ambiguity that would cause destructive deletion, excessive
collection, or uncontrolled exposure is **Blocking**.

---

## 16. Controls that must remain post-provisioning

The following controls cannot honestly be claimed as verified at Gate 17:

- final DNS resolution;
- live HTTPS/certificate behavior;
- live Microsoft Entra callback behavior;
- live GitHub OAuth callback behavior;
- GitHub App access to an authorized private team repository;
- Key Vault runtime retrieval;
- Application Insights ingestion;
- Log Analytics ingestion;
- action-group delivery;
- Container App restart alert;
- HTTP 5xx alert;
- PostgreSQL `is_db_alive` alert;
- PostgreSQL `storage_percent` alert;
- live `/health`;
- live `/ready`;
- live PostgreSQL backup settings;
- Azure PostgreSQL point-in-time restore;
- separate recovery server;
- private recovery networking;
- Alembic compatibility against the recovery candidate;
- measured RTO/RPO;
- controlled rollback/cutover;
- production authentication and authorization against the deployed system.

Classification: **Requires post-provisioning validation**.

These items do not block Gate 17 merely because they require live resources.
They do block student access until Post-Provisioning Production Acceptance.

---

## 17. Gate 17 decision record

Gate 17 approved: **2026-08-19**

The authorized production/course owner approved Gate 17 GO and authorized
**controlled Azure provisioning** after review of the source-controlled,
CI-validated, operator-configured, security, cost, and retention evidence.

| Control | Classification | Owner | Evidence | Result | Rationale / Follow-up |
|---|---|---|---|---|---|
| Prior gates / CI | Verified in CI | Engineering | CI runs and gate contracts | PASS | Prior gates are closed and the full regression suite is green. |
| Production security review | Blocking | Security reviewer | `docs/operations/GATE17_PRODUCTION_SECURITY_REVIEW.md` | APPROVED | Formal reviewer approval is recorded and no unresolved blocking production-security findings remain. |
| GitHub production environment | Operator-configured | Deployment owner | GitHub production environment | PASS | Environment exists, production configuration is environment-scoped, deployment is restricted to `main`, and release validation remains mandatory. |
| Azure OIDC / federated identity | Operator-configured | Deployment owner | Azure/GitHub configuration | PASS | Dedicated deployment application and production-environment federated trust are configured. The deployment principal had zero Azure resource authority before Gate 17 GO. |
| Deployment variables/secrets | Operator-configured | Deployment owner | Presence/scope inspection | PASS | Required production variables and protected secrets are present at production-environment scope. Secret values are not recorded here. |
| Production-test student configuration | Operator-configured | Identity owner | Presence/scope inspection | PASS | Exact bounded production-test identity configuration is present without creating a general external-domain authorization path. |
| Microsoft Entra | Operator-configured | Identity owner | Configuration record | PASS | Single-tenant human-authentication application, production callback plan, client configuration, and bounded identity policy are established. |
| GitHub App | Operator-configured | Integration owner | Configuration record and security review | PASS | Organization-owned, account-bounded, least-privilege read-only repository access is configured. |
| GitHub OAuth | Operator-configured | Integration owner | Configuration record | PASS | Production OAuth identity-linking application, callback plan, client ID, and protected secret are configured. |
| OpenAI | Operator-configured | AI/service owner | Production project, configuration, and regression evidence | PASS | Dedicated production project/key, source-controlled models, $40 hard limit, fail-closed behavior, and `store: false` are established. |
| Hostname/callback plan | Operator-configured | Deployment owner | Configuration plan | PASS | `https://simulator.etisframework.org` is the canonical HTTPS origin and Entra/GitHub OAuth callback plans are aligned. |
| Budget/cost notification | Operator-configured | Service owner | `docs/operations/GATE17_COST_CONTROL_PLAN.md` | PASS | $75 monthly Azure budget posture and notification thresholds are approved. Live Azure budget behavior remains post-provisioning. |
| Retention decisions | Deferred with explicit acceptance | Course/institutional owner | `docs/operations/GATE17_RETENTION_DECISION.md` | PASS | Preservation-first posture is approved; unresolved institutional calendar periods have an explicit owner and completion point. |
| Live Azure controls | Requires post-provisioning validation | Operations | Post-Provisioning Production Acceptance | NOT YET TESTABLE | Azure production resources do not yet exist. These controls remain mandatory before student access. |

### Gate 17 Azure boundary

No production Azure resource group exists before Gate 17 GO.

Gate 17 GO authorizes the controlled Azure bootstrap sequence:

1. create the approved empty production resource group;
2. assign the dedicated GitHub deployment principal only the approved
   resource-group-scoped deployment roles;
3. confirm the deployment principal has no subscription-wide deployment role;
4. run the validated production deployment workflow through the protected
   GitHub production environment.

This authorization permits deployment only. It does not constitute production
acceptance.

---

## 18. Current decision

Current Gate 17 decision: **GO**

Gate 17 GO was approved on **2026-08-19**.

The decision authorizes **controlled Azure provisioning** under the approved
bootstrap boundary.

Gate 17 GO is supported by:

- successful prior gates and current CI evidence;
- an approved Production Security Review;
- verified operator configuration for production deployment and integrations;
- an approved cost-control posture;
- retention decisions classified **Deferred with explicit acceptance**;
- explicit preservation of all live controls for later validation.

Live Azure controls remain **Requires post-provisioning validation**.

Gate 17 GO does not authorize student production use.

**Student access remains prohibited** until
**Post-Provisioning Production Acceptance** is explicitly GO.

The next lifecycle stage is controlled Azure bootstrap and deployment followed
by production acceptance testing.

