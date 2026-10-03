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

For v0.18.0, verify:

- source version in `apps/api/app/version.py` matches FastAPI/OpenAPI, `/health`, citation metadata, release notes, and all 12 paired manuals;
- source Bicep defaults are `minReplicas=1`, `maxReplicas=5`, and live drift checks agree;
- accepted production reasoning validation/planning are `shadow` / `shadow`, explicitly selected; fallback defaults remain `legacy` and student-visible authority remains legacy;
- current dependency pins and every open advisory are checked against the current dependency graph; do not dismiss alerts solely because a local environment has newer packages;
- merged SHA, protected workflow run, image/revision and live smoke are recorded before tagging/publishing;
- every manual PDF was regenerated from its matching DOCX and every rendered page inspected.

The August acceptance snapshot reported `0.15.0`; v0.16.0 and v0.17.0 are historical releases. Preserve those records rather than rewriting them with the new version. See [`releases/v0.18.0.md`](releases/v0.18.0.md).

## 6. Final visibility review

Before clicking **Change visibility → Public**:

- inspect the GitHub repository landing page as an unauthenticated user;
- verify issue templates and security-policy links;
- verify the license is detected as Apache-2.0;
- confirm no unintended branches/tags or releases expose sensitive artifacts;
- confirm README links render correctly;
- decide whether GitHub Discussions should be enabled for adopter/community questions.

Document who approved the public release and the commit SHA that was reviewed.
