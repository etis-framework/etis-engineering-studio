# Contributing to ETIS Engineering Studio

ETIS Engineering Studio is an open-source engineering-education project. Contributions are welcome from instructors, students, researchers, engineers, and institutions when they preserve the system's educational, security, evidence-integrity, and governance boundaries.

By submitting a contribution, you agree that your contribution may be distributed under the repository's Apache License 2.0. No separate contributor license agreement is currently required.

## Before contributing

- Read `README.md`, `GOVERNANCE.md`, `SECURITY.md`, and `docs/ARCHITECTURE.md`.
- For institutional deployment work, also read `docs/INSTITUTIONAL_ADOPTION.md` and `docs/PUBLIC_DEPLOYMENT_SECURITY.md`.
- Do not open a public issue for a suspected vulnerability; follow `SECURITY.md`.
- Never include student data, private repository content, production credentials, tokens, database exports, or institution-confidential information in issues or pull requests.

## Working model

1. Start from current `main`.
2. Create a narrowly scoped branch.
3. Make the smallest coherent change set that solves the identified problem.
4. Do not weaken tests, authorization, evidence integrity, or production validation merely to make a change pass.
5. Run validation appropriate to the change.
6. Update durable documentation when behavior changes.
7. Push the branch and open a pull request using the repository template.
8. Merge only after required CI and review are complete.

Maintainers may decline changes that broaden authority, reduce evidence integrity, create hidden grading behavior, weaken privacy/security controls, or make the system harder for institutions to operate safely.

## Change categories and validation

### Documentation/governance-only changes

Changes limited to Markdown, license/community files, issue/PR templates, CODEOWNERS, or citation metadata do not require the application test suite unless they also modify a file consumed by runtime or tests. Validate:

- repository status/inventory;
- Markdown links and file references;
- YAML/CFF syntax where applicable;
- no secrets or sensitive data introduced;
- `git diff --check`;
- staged-diff review.

Do not modify `tests/fixtures/**` under the assumption that Markdown there is documentation; those files are test inputs.

### Application, authorization, evidence, review, migration, workflow, or IaC changes

Run the complete local suite plus focused tests for the affected boundary. PostgreSQL-specific and production-container/IaC proofs remain CI-owned where local prerequisites are unavailable.

At minimum, preserve:

- one Alembic head;
- fail-closed production configuration;
- role/term/team authority boundaries;
- immutable frozen evidence;
- exact GitHub repository verification;
- side-effect-free GET semantics where required;
- no retained GitHub OAuth access token;
- no PAT repository access path;
- no weakening of institutional or GitHub identity controls.

## Repository hygiene

Never commit:

- `.env` or local secret files;
- database dumps or local SQLite databases;
- Azure/cloud credentials or tokens;
- GitHub App private keys;
- OAuth client secrets;
- OpenAI API keys;
- student-sensitive exports;
- private repository content copied for debugging;
- local validation archives;
- editor/OS metadata;
- patch/helper artifacts intended only for local repair.

Use synthetic or redacted data for bugs and tests.

## Pull request expectations

A good PR explains:

- the problem and intended educational/operational outcome;
- security/authorization implications;
- evidence/review implications;
- migrations or deployment implications;
- validation performed;
- documentation updated;
- screenshots for meaningful UI changes, with all sensitive data removed.

## Institutional adaptations

Institution-specific forks are expected. If a change is broadly useful, consider contributing it upstream rather than maintaining a permanent fork. Integration changes for non-Entra identity providers, non-GitHub source control, or other clouds should isolate provider-specific behavior behind clear interfaces rather than weakening current security contracts.

## Documentation authority

Use `docs/README.md` as the documentation map. Historical gate documents may remain as decision records, but current behavior belongs in current architecture/operations/adoption documentation. Release history belongs in `CHANGELOG.md` and Git history rather than root-level patch overlays.
