# Support

ETIS Engineering Studio support depends on how the project is being used.

## Institutional adopters

Start with:

- `docs/INSTITUTIONAL_ADOPTION.md`
- `docs/PUBLIC_DEPLOYMENT_SECURITY.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/operations/README.md`

For a reproducible software defect, open a GitHub issue using the bug template. Remove secrets, student information, private repository contents, tenant identifiers that are not necessary to reproduce the issue, and confidential logs.

For an enhancement proposal, use the feature-request template and describe the educational or operational outcome rather than only the desired implementation.

The upstream project cannot provide institution-specific legal, FERPA/privacy, accessibility, identity-governance, procurement, cloud-support, or AI-policy approval. Each adopter remains responsible for those decisions.

## Students in an adopting course

Students should use the support channel designated by their instructor/institution, not the upstream GitHub repository, for course-specific access, team assignment, grading, deadlines, or private repository issues.

Do not post private repository content, identity information, or screenshots containing sensitive data to a public forum.

## Teaching staff

Use instructor surfaces to distinguish identity/access, section/team assignment, repository authorization, evidence availability, and Review Room/session problems. Do not manually force-bind repositories or edit production database state to bypass normal authorization.

## Operators/maintainers

For the reference Azure deployment, start with:

- `docs/operations/PRODUCTION_OPERATIONS_RUNBOOK.md`
- `docs/operations/INCIDENT_RESPONSE_RUNBOOK.md`
- `docs/operations/DATABASE_RECOVERY_RUNBOOK.md`
- `docs/operations/POST_PROVISIONING_PRODUCTION_ACCEPTANCE.md`

Institutional adopters should copy these patterns into institution-owned runbooks with local contacts, escalation paths, RTO/RPO decisions, budgets, and retention requirements.

## Security issues

Follow `SECURITY.md`. Security-sensitive reports must remain private.
