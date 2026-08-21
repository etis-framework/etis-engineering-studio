# ETIS Engineering Studio — Production-Accepted Build Report

**Acceptance date:** 2026-08-21
**Source commit:** `db57225e98cb83499e6aa606740239a0b5bc697f`
**Application-reported version:** `0.15.0`
**Production acceptance:** **GO**

## 1. Build objective

This report supersedes the former v0.15 pre-Azure build report. It records the production-accepted Wave 1 baseline after production integration, GitHub repository-onboarding hardening, authorization hardening, instructor/student UX acceptance fixes, Azure deployment, and live post-provisioning validation.

The accepted release criterion is end-to-end behavior: an authorized user action must preserve the correct identity, section/team authority, repository/evidence context, review purpose, historical record, and security boundary through the complete workflow.

## 2. Accepted product scope

The production baseline includes:

- Microsoft Entra authentication and Loyola-domain production identity policy.
- Course/term/section/team/student administration and lifecycle authorization.
- Course Owner, Instructor, TA, Reviewer, and Student role separation.
- GitHub identity linking with Studio-session-bound OAuth callback handling.
- Candidate repository nomination separate from verified repository authority.
- Personal owner resolution using immutable GitHub account IDs.
- Organization repository GitHub App authorization/request flow.
- GitHub App **Only select repositories** enforcement and exact-repository installation tokens.
- Bounded production-test starter-kit exception controlled by exact configured test identity.
- Controlled repository-onboarding reset preserving historical evidence/reviews.
- Strict server-side GitHub URL validation and canonicalization.
- Frozen evidence snapshots, provenance, FACT/REVIEW separation, evidence disputes, and corrected finding memory.
- Board Review, Focused Review, and Review Findings modes.
- Student recommendation lifecycle, semantic coaching, evidence challenge, and persistent review history.
- Instructor shared section context, team detail, multi-student active-review visibility, evidence/review drill-down, AI economics, and semester administration.
- Browser Back/Forward navigation and GitHub authorization return-to-Studio flow.
- Azure production deployment, managed identity, Key Vault, private PostgreSQL, telemetry, alerting, backup/PITR, and rollback assets.

## 3. Local and CI validation

Across the production-hardening and acceptance-fix branches, the following validation gates were repeatedly executed before merge:

- complete local `pytest` suite;
- focused repository-onboarding/security regression suites;
- Python compilation;
- `git diff --check` and staged-diff checks;
- one Alembic migration head;
- GitHub Actions workflow YAML parsing;
- PostgreSQL-specific CI tests;
- pinned Bicep compilation in CI and the manual release gate;
- production-container smoke tests including required `GITHUB_APP_SLUG` configuration;
- repository/build-context hygiene checks.

GitHub CI was green before each accepted merge and the protected Azure deployment workflow completed successfully for the production baseline.

## 4. Live production acceptance evidence

### Identity and authorization

- Normal `luc.edu` Microsoft Entra sign-in was live-tested with the Course Owner account and returned to the correct instructor surface.
- No second ETIS-specific password or separate ETIS-specific Authenticator enrollment was observed.
- The bounded external production-test student exercised the student surface without broadening normal domain authorization.

### GitHub identity and repository onboarding

Live tests passed for:

- GitHub account relinking and account selection;
- switching to a second GitHub identity and returning to the intended identity;
- logout/login persistence;
- student inability to directly replace a verified repository;
- Course Owner/Instructor repository-onboarding reset;
- preservation of prior evidence and review history after reset;
- bounded public starter-kit production-test fixture;
- personally owned private repository (`usranger290/LUC_CS272`);
- organization-owned repository (`etis-framework/comp330-f26-production-acceptance`);
- GitHub App owner-targeted installation routing;
- **Only select repositories** configuration;
- separate Step 1 authorization and Step 2 exact-repository verification;
- GitHub App Setup URL/Redirect-on-update return flow;
- browser Back/Forward navigation after deployment.

Automated Alice/Bob/Carol scenarios cover multi-student owner/non-owner/team-wide propagation behavior that was not reproduced live with multiple production student identities.

### Azure and application runtime

- Container App provisioning state: `Succeeded`.
- Running status: `Running`.
- `/health`: HTTP 200 with production security headers.
- `/ready`: HTTP 200 with `database_connected=true` and `migration_current=true`.
- Alembic current/head revision at acceptance: `d42b8f5ae201`.
- User-assigned managed identity: `etis-studio-prod-runtime`.
- Runtime secrets resolve through Azure Key Vault using `Key Vault Secrets User` at Key Vault scope.
- Application Insights is workspace-connected to Log Analytics.
- Log Analytics retention: 30 days.
- Production alert rules and the operations action group are enabled.

### Database recovery

PostgreSQL production posture at acceptance:

- PostgreSQL 16;
- `Standard_B1ms`, 32 GB;
- private network access only;
- 7-day backup retention;
- geo-redundant backup disabled;
- HA disabled.

A real non-destructive point-in-time restore was performed on 2026-08-21. The temporary restored server:

- reached `Ready`;
- preserved private subnet/private DNS configuration;
- accepted a real connection from the production Container App;
- contained Alembic revision `d42b8f5ae201`;
- contained 21 application tables and restored course/team data.

The temporary recovery server was then deleted and confirmed absent.

### Rollback and cost control

- ACR retains multiple immutable commit-SHA application images, supporting rollback by redeploying a prior known-good image in Single revision mode.
- Production resource-group budget: `$100/month`.
- Actual-cost notifications: 50%, 80%, 100%.
- Accepted runtime scaling: `minReplicas=1`, `maxReplicas=5`.

## 5. Residual acceptance notes

These are documented limitations, not current release blockers:

1. The production student team used for live acceptance contains one student. Multi-student owner/non-owner repository propagation is automated-test/CI proven rather than live proven.
2. Production rollback capability was verified through retained immutable images; production was not deliberately rolled backward solely for acceptance.
3. The application health payload still reports version `0.15.0` even though substantial production-integration hardening followed that baseline. This is a version-labeling/documentation debt, not evidence that old code is deployed.
4. An intermittent 15–25 second page-load observation became non-reproducible. The production Container App was changed to keep one minimum replica warm, reducing scale-to-zero cold-start risk.
5. **IaC/runtime drift:** `infra/azure/app.bicep` currently defaults `minReplicas` to `0`, while the accepted production runtime is `1`. Do not assume a future deployment will preserve the accepted warm-replica setting until that source-controlled default or deployment parameter is reconciled in a separate, tested infrastructure change.

## 6. Release posture

**Production Post-Provisioning Acceptance: GO.**

The Studio may remain deployed for the semester. Code and production configuration should now be treated as frozen unless an actual defect, security issue, required course change, or deliberately scheduled enhancement justifies a new controlled branch/PR/CI/deployment cycle.
