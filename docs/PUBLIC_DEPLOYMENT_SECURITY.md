# Public Deployment Security Checklist

Use this checklist when deploying ETIS Engineering Studio outside the ETIS Framework reference environment. It is intentionally fail-closed and should be adapted to local institutional policy.

## Identity

- [ ] Institution owns the identity application registration.
- [ ] Tenant/domain restrictions are explicit.
- [ ] Normal institutional MFA remains enforced.
- [ ] Studio does not manage user passwords.
- [ ] Course/term/section/team authorization is database-backed and current.
- [ ] Archived terms cannot grant current authority.
- [ ] Staff read authority is separate from student mutation authority.

## GitHub

- [ ] Institution owns its GitHub App/OAuth registration.
- [ ] GitHub App is configured for the accounts/organizations where repositories live.
- [ ] **Only select repositories** is required; `all repositories` must fail closed.
- [ ] Repository tokens are scoped to the exact repository.
- [ ] Personal repository ownership uses immutable GitHub account ID.
- [ ] Organization approvals use GitHub's native organization authorization/request process.
- [ ] GitHub OAuth state is bound to the initiating Studio session.
- [ ] GitHub OAuth access tokens are not retained.
- [ ] No PAT path exists.
- [ ] Setup URL points to the institution's `/github/setup-complete` endpoint if using the upstream flow.

## Secrets and cloud identity

- [ ] No production secret is committed to Git.
- [ ] Runtime secrets come from an institution-owned secret store.
- [ ] Application runtime uses managed/workload identity where possible.
- [ ] Runtime identity has only the minimum secret-read and resource permissions required.
- [ ] Deployment authority is separated from application runtime authority.

## Database

- [ ] PostgreSQL is not exposed publicly unless an institution has explicitly accepted that risk and configured controls.
- [ ] Migrations are applied through a controlled deployment/migration path.
- [ ] `/ready` fails when the database is unavailable or migrations are not current.
- [ ] Backup retention is explicit.
- [ ] A real non-destructive restore drill has been performed before production GO.
- [ ] RTO/RPO are documented locally.

## Application/runtime

- [ ] HTTPS only; HSTS and security headers verified.
- [ ] Health and readiness endpoints return expected status.
- [ ] Required production settings fail closed when absent.
- [ ] At least one warm replica is configured if cold-start latency is unacceptable.
- [ ] Previous immutable images are retained for rollback.

## AI

- [ ] Institution owns the AI provider account/project and API credentials.
- [ ] Cost/budget controls are configured.
- [ ] Only bounded evidence/context is sent to the provider.
- [ ] AI is advisory, not grading/decision authority.
- [ ] Students can challenge/correct REVIEW interpretation without rewriting FACT evidence.

## Observability and operations

- [ ] Application telemetry is enabled.
- [ ] Logs have an explicit retention period.
- [ ] Alerts cover availability, 5xx, restarts, database availability/storage, and other locally important failures.
- [ ] Action-group recipients are current and tested.
- [ ] Budget alerts are configured.
- [ ] Incident-response and database-recovery runbooks identify real local operators.

## Privacy and course lifecycle

- [ ] Roster import collects only data actually required.
- [ ] Student-sensitive data is not written to public logs/issues/repos.
- [ ] Unsent drafts remain private.
- [ ] Evidence/review retention policy is institution-approved.
- [ ] Archiving removes current student authority without destroying required history.
- [ ] Grades and unrelated official records remain in the institution's authoritative systems.

## Before GO

Record evidence for every applicable item. Any accepted exception should have an owner, rationale, and follow-up date.
