# Public Repository Release Checklist

This checklist is for the upstream ETIS Engineering Studio repository before changing GitHub visibility from private to public. It is separate from application production acceptance.

## 1. Complete-history review

A clean current tree is not enough. Review **all reachable Git history, branches, and tags** for:

- API keys, passwords, OAuth secrets, GitHub App private keys, cloud credentials, database URLs, tokens;
- `.env` files, database dumps, archives, backups, logs, or local validation artifacts;
- student rosters, grades, student identifiers, private repository contents, or confidential screenshots;
- private institutional documents or operational exports.

If a real secret was ever committed, rotate/revoke it even if the commit is later removed from history.

## 2. Repository security settings

Before or immediately after public visibility:

- enable secret scanning and push protection where available;
- enable Dependabot alerts/updates;
- enable private vulnerability reporting;
- protect `main` and require CI before merge;
- keep production deployment behind a protected GitHub Environment;
- review GitHub Actions permissions and ensure untrusted fork PRs cannot access production secrets or OIDC deployment authority;
- review collaborators/teams and remove obsolete access.

The current CI workflow is designed to run PR validation without production secrets; the manual deployment workflow uses a protected production environment. Re-review these controls before visibility change.

## 3. Community/governance files

Verify these are present and current:

- `README.md`
- `LICENSE` and `NOTICE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `GOVERNANCE.md`
- `SECURITY.md`
- `SUPPORT.md`
- `CITATION.cff`
- `.github/CODEOWNERS`
- pull-request and issue templates

## 4. Institutional adoption clarity

- upstream docs distinguish the ETIS Framework reference deployment from an adopter's deployment;
- adopters are told to create their own Entra/GitHub/cloud/OpenAI credentials;
- Loyola/course-specific examples are labeled as examples/context rather than universal requirements;
- no production-test identity is presented as a general access mechanism;
- licensing and trademark expectations are explicit.

## 5. Source/release consistency

Before calling the public repository an authoritative deployable release, reconcile known source/runtime drift. At the 2026-08-21 reference baseline:

- accepted runtime uses Container App `minReplicas=1`;
- `infra/azure/app.bicep` still defaults `minReplicas=0`;
- health metadata still reports application version `0.15.0` even though production-hardening commits followed that original baseline.

These do not prevent publication, but they should be reconciled in a normal code/IaC PR before the next release intended as a reproducible institutional deployment baseline.

## 6. Final visibility review

Before clicking **Change visibility → Public**:

- inspect the GitHub repository landing page as an unauthenticated user;
- verify issue templates and security-policy links;
- verify the license is detected as Apache-2.0;
- confirm no unintended branches/tags or releases expose sensitive artifacts;
- confirm README links render correctly;
- decide whether GitHub Discussions should be enabled for adopter/community questions.

Document who approved the public release and the commit SHA that was reviewed.
