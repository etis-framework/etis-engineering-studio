# Wave 1 Acceptance

**Status:** **PASS / Production GO — 2026-08-21**

Wave 1 was accepted for controlled semester use after source/CI gates and live Post-Provisioning Production Acceptance.

## Accepted capabilities

- A1-A6 machine-readable phase contracts load; A1/A2 have the deepest current review behavior.
- Unauthorized/non-current users fail closed.
- Students see only current authorized team context.
- Repository evidence is frozen at a known commit/snapshot.
- Starter-kit scaffold is not misrepresented as team-completed evidence.
- Weak/missing evidence produces consequence-oriented engineering challenge rather than simple missing-file grading.
- Students can ask, disagree, provide contrary evidence, receive progressive coaching, and state a recommendation without being handed a hidden answer.
- Board Review, Focused Review, and Review Findings are distinct and locked per session.
- Instructors can see bounded team/evidence/review activity without seeing unsent drafts or gaining student impersonation authority.
- Repository onboarding is team-wide only after exact GitHub verification.
- Personal and organization repository flows passed production acceptance.
- Automated tests/CI, health, readiness, production migrations, Bicep compilation, and container smoke gates pass.
- Azure secrets, HTTPS, logging, alerts, backups/PITR, rollback assets, and cost budget are configured/accepted.
- A real PostgreSQL PITR restore drill passed.

## Live versus automated evidence

Live production evidence includes Entra instructor login, the bounded production-test student, GitHub identity linking/relinking, starter-kit fixture, personal private repository, organization repository, repository reset/history preservation, browser navigation, GitHub return flow, Key Vault/managed identity, health/readiness, monitoring configuration, PITR recovery, and budget configuration.

Multi-student GitHub owner/non-owner propagation is automated/CI proven rather than live-proven with multiple production student identities.

See:

- `BUILD_REPORT.md`
- `docs/PRODUCTION_BASELINE.md`
- `docs/operations/POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md`
