# Production Baseline — 2026-08-21

> **Public/adopter note:** this document records the ETIS Framework reference deployment. It is evidence for the upstream project, not production acceptance for another institution. Adopters must provision their own identity, GitHub, cloud, AI, privacy, retention, monitoring, backup, and cost controls.

**Status:** **GO**
**Source commit:** `db57225e98cb83499e6aa606740239a0b5bc697f`
**Production hostname:** `https://simulator.etisframework.org`

This document is the concise source of truth for the production-accepted ETIS Engineering Studio baseline after the 2026-08-21 Post-Provisioning Production Acceptance campaign.

## Application posture

ETIS Engineering Studio is approved for normal semester operation. The service is browser-based, hosted in Azure, and intentionally keeps students as the responsible engineers. AI reviewers are bounded advisers; they do not grade, fabricate evidence, or become the decision authority.

The v0.16.0 release aligns FastAPI application and `/health` version metadata to `0.16.0`. The 2026-08-21 production-acceptance snapshot originally reported `0.15.0`; that historical acceptance evidence remains valid and is preserved in the build and acceptance records.

## Identity and authorization

- Microsoft Entra authenticates institutional users.
- Production configuration uses an explicit tenant UUID and allowed institutional domain `luc.edu`.
- Studio does not manage user passwords.
- Current application authority is derived from database course/term/section/team/role state.
- `CourseTerm.status` is authoritative: `setup` → `active` → `archived`.
- Archived terms cannot grant current student/team/reviewer authority.
- Course Owner, Instructor, TA, Reviewer, and Student privileges are separate.
- The bounded production-test student is exact-principal configured; Gmail is not generally authorized.

## GitHub model

GitHub identity linking and repository authorization are separate.

Repository state:

```text
No repository
  → Candidate repository
  → Owner authorization required
  → Verified team repository
```

Production rules:

- candidate URL is not authoritative evidence;
- GitHub URL validation is server-side and HTTPS-only;
- personal repository ownership uses immutable GitHub account ID;
- organization repositories use GitHub's organization authorization/request flow;
- GitHub App is public/installable on authorized external accounts;
- GitHub App Setup URL: `https://simulator.etisframework.org/github/setup-complete`;
- Redirect on update is enabled;
- installations must use **Only select repositories**;
- `all repositories` fails closed;
- installation tokens are requested for the exact repository only;
- no PAT path exists;
- GitHub OAuth access tokens are not retained;
- OAuth callback is bound to the initiating Studio session/user;
- verified repositories can be reset only through bounded staff recovery, preserving historical evidence/reviews.

Live production acceptance passed for both a personally owned private repository and an organization-owned repository.

## Review/evidence model

- frozen repository snapshots are immutable;
- FACT evidence and REVIEW interpretation remain distinct;
- corrected REVIEW findings do not rewrite snapshot evidence;
- same-snapshot corrections prevent repeated false findings;
- exactly one review purpose is active per session: Board Review, Focused Review, or Review Findings;
- review purpose is locked once the session begins;
- team evidence is shared; student coaching/review conversation is individual;
- instructors can view persisted conversations but not unsent drafts;
- staff read authority does not imply authority to impersonate student review actions.

## Azure production resources

Production resource group: `etis-studio-prod`.

Accepted live resources include:

- Azure Container App `etis-studio-prod`;
- Azure Container Registry `etisstudioprodev3bgd5nmvfg4`;
- PostgreSQL Flexible Server `etis-studio-prod-pg-ev3bgd5nmvfg4`;
- Key Vault `etis-studio-prod-kv-ev3b`;
- user-assigned managed identity `etis-studio-prod-runtime`;
- Application Insights `etis-studio-prod-appi`;
- Log Analytics `etis-studio-prod-law`.

## Runtime security and secrets

The Container App uses the user-assigned runtime identity. It has `Key Vault Secrets User` at the production Key Vault scope.

Container App secrets reference Key Vault entries for:

- database URL;
- session secret;
- Entra client secret;
- GitHub App private key;
- GitHub OAuth client secret;
- OpenAI API key.

The application consumes those values by Container App `secretRef`; secret values are not stored as literal source-controlled configuration.

## Health and readiness

Accepted live checks:

- Container App provisioning: `Succeeded`;
- running status: `Running`;
- `/health`: HTTP 200;
- `/ready`: HTTP 200;
- `database_connected=true`;
- `migration_current=true`;
- Alembic current/head at acceptance: `d42b8f5ae201`.

Security headers include HSTS, CSP, frame denial, content-type protection, referrer policy, and restrictive permissions policy.

## Scaling

Accepted live runtime:

- minimum replicas: **1**;
- maximum replicas: **5**.

The one-minimum-replica setting was selected after acceptance testing observed intermittent long reloads that could not later be reproduced. Keeping one warm replica avoids normal scale-to-zero cold starts.

**Known source/runtime drift:** `infra/azure/app.bicep` currently defaults `minReplicas` to `0`. Reconcile this in a separate tested IaC change before assuming a future deployment will preserve `minReplicas=1`.

## Observability and alerting

- workspace-based Application Insights connected to Log Analytics;
- Log Analytics retention: 30 days;
- production operations action group enabled with an operational email receiver;
- enabled alerts:
  - Container App HTTP 5xx;
  - Container App restart count;
  - PostgreSQL not-alive;
  - PostgreSQL storage percentage.

## Database durability and recovery

Accepted PostgreSQL posture:

- PostgreSQL 16;
- `Standard_B1ms` Burstable;
- 32 GB storage;
- private network access only;
- 7-day automatic backup retention;
- geo-redundant backup disabled;
- high availability disabled.

A real PITR recovery drill passed on 2026-08-21. The restored server was validated for private networking, schema revision, connection, table count, and restored course/team data, then deleted.

## Rollback

Azure Container Apps uses Single revision mode. Rollback is therefore operationally based on redeploying a prior immutable ACR image rather than traffic-shifting to a concurrently retained active revision.

Multiple prior commit-SHA image tags were verified present in ACR during acceptance.

## Cost control

Production resource-group budget:

- amount: **$100/month**;
- actual-cost notifications: **50%, 80%, 100%**;
- budget alerts do not automatically stop resources.

## Accepted residual notes

- multi-student GitHub owner/non-owner propagation is automated/CI proven rather than live-proven with multiple production student identities;
- a production rollback was not deliberately executed solely for acceptance;
- the intermittent 15–25 second load observation is currently non-reproducible and should be captured with browser Network tooling if it returns;
- IaC/runtime `minReplicas` drift should be reconciled before the next infrastructure-changing deployment.
