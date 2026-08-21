# Security Policy

ETIS Engineering Studio handles institutional identity, private source repositories, student/team authorization, AI interactions, and production credentials. Security reports must be handled privately.

## Supported branch

`main` is the currently supported upstream branch. Maintainers may provide additional version-specific guidance in GitHub Security Advisories when necessary.

## Reporting a vulnerability

**Do not open a public GitHub issue for a suspected vulnerability.**

For the public repository, use GitHub's **private vulnerability reporting** feature when enabled under the repository's Security area. If that feature is unavailable, contact the project maintainer privately using the contact information published by the ETIS Framework organization or maintainer profile.

Include only what is necessary to reproduce and assess the issue. Do not send live credentials, student records, private repository contents, access tokens, database dumps, or unrelated personal information. If a credential may be exposed, identify the credential class without pasting the secret itself.

Maintainers should acknowledge reports privately, assess severity and affected versions, coordinate remediation, rotate exposed credentials when necessary, and use GitHub Security Advisories for coordinated disclosure when appropriate.

## Security invariants

Changes must preserve these boundaries:

- production course access derives from current course/term/section/team authority;
- archived terms cannot grant current authority;
- staff read access does not imply student mutation authority;
- institutional authentication remains external to Studio; Studio does not manage user passwords;
- GitHub identity linking is separate from repository authorization;
- a typed GitHub URL is only a candidate until exact repository verification succeeds;
- personal-repository owner authority uses immutable GitHub account ID;
- organization-repository access follows GitHub's organization authorization/request model;
- GitHub App installation scope must be **Only select repositories**; `all repositories` fails closed;
- installation tokens are requested for the exact repository only;
- PATs are not supported;
- GitHub OAuth access tokens are not retained;
- production secrets remain in a dedicated secret store and are not source-controlled;
- frozen evidence snapshots are immutable;
- corrected REVIEW interpretations do not rewrite underlying snapshot evidence;
- unsent student drafts remain browser-private and are not exposed to instructors;
- production configuration fails closed when required identity, database, GitHub App, or AI settings are missing.

## Public-repository precautions

Before making a fork or deployment public:

- scan the complete Git history and all branches/tags for secrets and sensitive data;
- enable secret scanning/push protection where available;
- protect production deployment environments;
- ensure fork-originated pull requests cannot obtain deployment credentials;
- keep real rosters, private repository evidence, logs containing student data, and production exports out of the repository.

See `docs/PUBLIC_RELEASE_CHECKLIST.md` and `docs/PUBLIC_DEPLOYMENT_SECURITY.md`.

## Credential response

If a production credential is suspected to be exposed:

1. contain access;
2. rotate/revoke the affected credential at its provider;
3. update the institution's secret store/protected deployment configuration;
4. redeploy only if runtime configuration requires it;
5. validate health/readiness;
6. verify the affected integration;
7. record the incident privately;
8. assess whether a security advisory or disclosure is required.

The ETIS Framework production runbook is in `docs/operations/INCIDENT_RESPONSE_RUNBOOK.md`; adopters should maintain an institution-specific equivalent.
