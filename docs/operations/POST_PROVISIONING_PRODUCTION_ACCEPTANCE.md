# Post-Provisioning Production Acceptance

**Decision:** **GO**
**Decision date:** 2026-08-21
**Accepted source commit:** `db57225e98cb83499e6aa606740239a0b5bc697f`

## 1. Purpose

Post-Provisioning Production Acceptance is the live-environment acceptance gate that follows Gate 17 and successful Azure deployment. It authorizes normal student production use only after controls that cannot be proven from source/CI have been exercised in the real environment.

This document records the 2026-08-21 acceptance result.

## 2. Decision boundary

Gate 17 GO authorized provisioning/deployment. It did not itself authorize student use.

Post-Provisioning Production Acceptance required evidence for:

- hostname/DNS/TLS;
- Microsoft Entra authentication;
- GitHub OAuth/App behavior;
- authorization boundaries;
- Key Vault/managed identity;
- health/readiness;
- PostgreSQL/migrations;
- observability/alerts;
- backup/PITR/recovery;
- rollback assets;
- cost controls;
- Wave 1 student/instructor production journeys.

## 3. Acceptance summary

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
| Real PITR restore drill | PASS | live recovery exercise |
| Restored schema/data validation | PASS | live recovery exercise |
| Immutable image rollback assets | PASS | live inventory |
| Production budget/alerts | PASS | live configuration |
| Browser Back/Forward | PASS | live |
| GitHub return-to-Studio UX | PASS | live |

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
- private personal repository `usranger290/LUC_CS272`;
- organization repository `etis-framework/comp330-f26-production-acceptance`.

The GitHub App was changed from private-to-owner-only installation to public/installable so approved personal repository owners can install it. This does not make any repository public.

Accepted GitHub App settings include:

- **Only select repositories**;
- Setup URL `https://simulator.etisframework.org/github/setup-complete`;
- Redirect on update enabled.

Step 1 authorization and Step 2 exact repository verification remain separate.

## 5. Secrets and managed identity

Container App uses user-assigned identity `etis-studio-prod-runtime`.

The identity has `Key Vault Secrets User` at the production Key Vault scope. The Container App secret definitions reference Key Vault for database, session, Entra, GitHub App, GitHub OAuth, and OpenAI secret values. Runtime environment variables consume those through secret references.

No secret values were recorded as acceptance evidence.

## 6. Health and readiness

Live `/health` returned HTTP 200 with production mode, semantic-coaching readiness, Entra readiness, GitHub identity-link readiness, and GitHub App readiness.

Live `/ready` returned HTTP 200 with:

- `database_connected=true`;
- `migration_current=true`;
- current revision `d42b8f5ae201`;
- head revision `d42b8f5ae201`.

## 7. Observability and alerts

Accepted live configuration:

- Application Insights `etis-studio-prod-appi`, status Succeeded;
- workspace-connected Log Analytics `etis-studio-prod-law`;
- 30-day log retention;
- operations action group enabled with email receiver;
- PostgreSQL storage alert enabled;
- Container App restart alert enabled;
- PostgreSQL not-alive alert enabled;
- HTTP 5xx alert enabled.

## 8. PostgreSQL backup/PITR

Accepted PostgreSQL state:

- PostgreSQL 16;
- server Ready;
- private network access disabled from the public Internet;
- 7-day backup retention;
- earliest restore point was visible through Azure;
- geo-redundant backup disabled;
- HA disabled.

A real temporary PITR server was restored to a point approximately ten minutes before the exercise. It reached Ready with the same private subnet/DNS posture. From the production Container App, the restored database returned:

- connection PASS;
- Alembic revision `d42b8f5ae201`;
- 21 tables;
- restored course-term data;
- restored team data.

The temporary PITR server was then deleted and ResourceNotFound confirmed cleanup.

## 9. Rollback

Container Apps uses Single revision mode. Production rollback is based on redeploying a retained immutable ACR commit-SHA image.

Acceptance verified the current image and multiple prior commit-SHA image tags. Production was not deliberately rolled back solely for acceptance.

## 10. Cost controls

Production resource-group budget was configured through Azure Resource Manager:

- amount: `$100`;
- time grain: monthly;
- 50% actual-cost notification;
- 80% actual-cost notification;
- 100% actual-cost notification.

Budget notifications are warnings, not automatic shutdown controls.

## 11. Scaling

During acceptance the Container App was changed from `minReplicas=0` to `minReplicas=1`, with `maxReplicas=5`, to avoid scale-to-zero cold starts during the semester.

The resulting revision became both LatestRevision and LatestReadyRevision and remained Running.

Known follow-up: source `infra/azure/app.bicep` still defaults `minReplicas` to `0` and should be reconciled separately.

## 12. Residual evidence notes

Accepted residual notes:

- normal Loyola student authorization was not live-tested with a second `luc.edu` student identity; the Loyola instructor identity and bounded student test identity covered the two sides of the flow, and student authorization is automated-tested;
- multi-student GitHub propagation was automated/CI proven, not live-proven with multiple production student identities;
- application rollback assets were live verified, but healthy production was not deliberately rolled backward;
- intermittent 15–25 second load behavior became non-reproducible; keep one warm replica and capture Network timing if it returns;
- application version metadata remains `0.15.0`.

## 13. Final decision

**GO.**

All blocking production controls required for Wave 1 controlled semester use have sufficient evidence. The application may remain deployed for the semester. Future changes must follow the normal branch/PR/CI/protected-deployment/targeted-acceptance process.
