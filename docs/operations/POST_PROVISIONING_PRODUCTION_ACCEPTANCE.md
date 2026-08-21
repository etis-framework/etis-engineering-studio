# Post-Provisioning Production Acceptance

**Decision:** **GO**  
**Decision date:** 2026-08-21  
**Accepted source commit:** `db57225e98cb83499e6aa606740239a0b5bc697f`

## 1. Purpose and decision boundary

**Post-Provisioning Production Acceptance** is the live-environment acceptance
review performed after Gate 17 authorized Azure provisioning and after the
production infrastructure/application were deployed.

Its purpose is to determine whether the deployed ETIS Engineering Studio is
safe and operationally ready for controlled **student access**. Before the
2026-08-21 decision, student access remained disabled until this review reached
an **explicit GO**. This document records that GO decision and the supporting
production evidence.

Gate 17 GO authorized provisioning/deployment. It did not itself authorize
student production use.

A successful deployment is not itself a go-live decision.

A successful `/ready` response is necessary but not sufficient for student
production authorization.

Post-Provisioning Production Acceptance required live evidence for:

- hostname, **DNS**, and **HTTPS**;
- **Microsoft Entra** authentication;
- **GitHub OAuth** identity linking and **GitHub App** repository access;
- authentication, authorization, and production **access controls**;
- Key Vault, managed identity, and production **secrets**;
- `/health` and `/ready`;
- PostgreSQL, **Alembic**, migrations, and private networking;
- Application Insights, Log Analytics, operational **logging**, alerts, and the
  Azure Monitor action group;
- database **backup**, **backups**, point-in-time restore, and recovery;
- RTO/RPO and rollback posture;
- cost/budget controls;
- Wave 1 student and instructor production journeys.

## 2. Acceptance summary

| Control | Result | Evidence classification |
|---|---|---|
| Production deployment workflow | PASS | CI + live |
| DNS / HTTPS / security headers | PASS | live |
| Loyola Entra sign-in | PASS | live instructor identity |
| Second ETIS-specific password/MFA enrollment | Not observed | live |
| Bounded external production-test student | PASS | live |
| GitHub identity link/relink/account switch | PASS | live |
| Personal private repository onboarding | PASS | live |
| Organization repository onboarding | PASS | live |
| GitHub App Only select repositories | PASS | live + automated |
| Exact repository verification/token scope | PASS | live + automated |
| Repository reset/history preservation | PASS | live + automated |
| Multi-student owner/non-owner propagation | PASS | automated/CI; not multi-student live |
| Managed identity / Key Vault | PASS | live configuration |
| Container App state | PASS | live |
| `/health` | PASS | live |
| `/ready` + DB + Alembic | PASS | live |
| Application Insights / Log Analytics | PASS | live configuration |
| Azure Monitor alerts/action group | PASS | live configuration |
| PostgreSQL backup retention | PASS | live configuration |
| Real point-in-time restore drill | PASS | live recovery exercise |
| Restored schema/data validation | PASS | live recovery exercise |
| Immutable image rollback assets | PASS | live inventory |
| Production budget/alerts | PASS | live configuration |
| Browser Back/Forward | PASS | live |
| GitHub return-to-Studio UX | PASS | live |

## 3. Production-test student identity

Production Acceptance exercised the deployed system with the deliberately
bounded, nonprivileged production-test student configured by the operator.
The configuration contract is:

- `ETIS_PRODUCTION_TEST_STUDENT_OID`
- `ETIS_PRODUCTION_TEST_STUDENT_EMAIL`
- `ETIS_PRODUCTION_TEST_STUDENT_ID`
- `ETIS_PRODUCTION_TEST_SECTION_KEY`
- `ETIS_PRODUCTION_TEST_TEAM_KEY`

The exception is bound to the configured **exact Entra Object ID**, roster
identity, the **designated production-test section**, and the **designated
production-test team**. It does not allow gmail.com generally or create a
second general external-student authentication path.

Acceptance verified that the test principal remained nonprivileged, followed
normal Studio course/team authorization, and could not use the exception to
obtain staff authority or substitute unrelated team/repository access.

## 4. GitHub acceptance details

The controlled production-test student exercised:

- initial GitHub identity link;
- relink to the same identity;
- switch to another available GitHub identity and return;
- logout/login persistence;
- verified-repository protection against direct student replacement;
- staff reset of repository onboarding;
- preservation of historical evidence/reviews;
- bounded public starter-kit fixture;
- a private personal repository;
- an organization-owned production-acceptance repository.

At least one **authorized private repository** was exercised. Repository
verification remained exact-repository scoped and fail closed.

The GitHub App was changed from private-to-owner-only installation to
public/installable so approved personal repository owners can install it. This
does not make any repository public.

Accepted GitHub App settings include:

- **Only select repositories**;
- Setup URL `https://simulator.etisframework.org/github/setup-complete`;
- Redirect on update enabled.

Step 1 authorization and Step 2 exact repository verification remain separate.

## 5. Secrets, managed identity, and evidence handling

The Container App uses the production user-assigned managed identity. The
identity has `Key Vault Secrets User` at the production Key Vault scope. The
Container App secret definitions reference Key Vault for database, session,
Entra, GitHub App, GitHub OAuth, and OpenAI secret values. Runtime environment
variables consume those through secret references.

**Do not record secret values** in acceptance or operational evidence. Do not
place an **access token**, **database password**, **API key**, **session cookie**,
private key, OAuth secret, or equivalent credential material in the evidence
record.

The acceptance record therefore documents control state and references without
embedding secret material.

## 6. Health and readiness

Live `/health` returned HTTP 200 with production mode, semantic-coaching
readiness, Entra readiness, GitHub identity-link readiness, and GitHub App
readiness.

Live `/ready` returned HTTP 200 with:

- `database_connected=true`;
- `migration_current=true`;
- current revision `d42b8f5ae201`;
- head revision `d42b8f5ae201`.

This verified live database connectivity and current Alembic migration state;
it did not substitute for the broader production-acceptance decision.

## 7. Observability, logging, and alerts

Accepted live configuration:

- **Application Insights** `etis-studio-prod-appi`, status Succeeded;
- workspace-connected **Log Analytics** `etis-studio-prod-law`;
- 30-day log retention and bounded operational **logging**;
- Azure Monitor **action group** enabled with the intended operations receiver;
- Container App `RestartCount` alert enabled;
- HTTP `5xx` alert enabled;
- PostgreSQL `is_db_alive` alert enabled;
- PostgreSQL `storage_percent` alert enabled.

These controls supplied live evidence for the alert definitions previously
established during Gate 16/Gate 17 pre-deployment hardening.

## 8. PostgreSQL backup, point-in-time restore, and recovery

Accepted PostgreSQL state:

- PostgreSQL 16;
- server Ready;
- public network access disabled;
- private VNet/subnet/DNS path preserved;
- 7-day **backup** retention;
- earliest restore point visible through Azure;
- geo-redundant backup disabled;
- HA disabled.

A real PostgreSQL **point-in-time restore** was performed to a **separate recovery server** rather than overwriting production. The recovered server
preserved **private networking** and reached Ready.

From the production application boundary, the restored database returned:

- connection PASS;
- Alembic revision `d42b8f5ae201`;
- 21 tables;
- restored course-term data;
- restored team data.

The temporary recovery server was then deleted and cleanup was verified.
Recovery timing and restore-point selection provide the live evidence used to
assess the documented **RTO** and **RPO** posture. The production operations and
database recovery runbooks remain authoritative for future recovery/cutover
work.

## 9. Rollback

Container Apps uses Single revision mode. Production **rollback** is based on
redeploying a retained immutable ACR commit-SHA image.

Acceptance verified the current image and multiple prior commit-SHA image tags.
Healthy production was not deliberately rolled backward solely to demonstrate
a mechanism already supported by retained immutable images.

## 10. Cost controls

Production resource-group budget was configured through Azure Resource Manager:

- amount: `$100`;
- time grain: monthly;
- 50% actual-cost notification;
- 80% actual-cost notification;
- 100% actual-cost notification.

Budget notifications are warnings, not automatic shutdown controls. See
`GATE17_COST_CONTROL_PLAN.md` for the historical Gate 17 pre-provisioning cost
plan and the production closeout differences.

## 11. Scaling

During acceptance the Container App was changed from `minReplicas=0` to
`minReplicas=1`, with `maxReplicas=5`, to avoid scale-to-zero cold starts during
the semester.

The resulting revision became both LatestRevision and LatestReadyRevision and
remained Running.

Known follow-up: source `infra/azure/app.bicep` still defaults `minReplicas` to
`0` and should be reconciled separately before a future deployment is expected
to preserve the accepted live value automatically.

## 12. Residual evidence notes

Accepted residual notes:

- normal Loyola student authorization was not live-tested with a second
  institutional student identity; the Loyola instructor identity and bounded
  student test identity covered the two sides of the flow, and student
  authorization is automated-tested;
- multi-student GitHub propagation was automated/CI proven, not live-proven
  with multiple production student identities;
- application rollback assets were live verified, but healthy production was
  not deliberately rolled backward;
- intermittent 15–25 second load behavior became non-reproducible; keep one
  warm replica and capture Network timing if it returns;
- application version metadata remains `0.15.0`.

## 13. Final decision

**GO.**

All blocking production controls required for Wave 1 controlled semester use
have sufficient evidence. Student production use is authorized, and the
application may remain deployed for the semester. Future changes must follow
the normal branch/PR/CI/protected-deployment/targeted-acceptance process.
