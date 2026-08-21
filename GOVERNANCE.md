# Governance

ETIS Engineering Studio uses a **maintainer-led open-source governance model**. The project welcomes institutional and community contributions while retaining a clear upstream decision authority so security, educational purpose, and production integrity do not drift through consensus-by-accident.

## Project steward

The ETIS Framework project steward/maintainer is responsible for:

- defining the upstream product and educational direction;
- approving releases and changes to security/authorization invariants;
- maintaining the reference architecture and production-acceptance standard;
- reviewing or delegating review of pull requests;
- coordinating security response;
- deciding when a change belongs upstream versus in an institution-specific extension.

`CODEOWNERS` records the current repository review ownership. Additional maintainers or institutional partners may be added over time.

## Decision principles

Upstream decisions prioritize, in order:

1. student/institution security and privacy;
2. evidence integrity and clear human responsibility;
3. educational value and engineering judgment;
4. operational reliability and maintainability;
5. interoperability and institutional adoption;
6. usability and implementation convenience.

A change that makes the UI easier but weakens authority, evidence, privacy, or auditability should not be accepted.

## Contribution lifecycle

- Issues and proposals establish the problem/outcome.
- Pull requests provide the implementation, validation, and documentation.
- CI must pass for code/infrastructure changes.
- Security-sensitive changes receive explicit maintainer review.
- Upstream acceptance does not automatically authorize deployment into the ETIS Framework production environment.

## Institutional forks and extensions

Institutions may fork, modify, and redistribute the project under Apache License 2.0. Institution-specific integrations are expected, especially for identity, learning-management systems, cloud infrastructure, privacy/retention policy, and AI governance.

Where possible, provider-specific adaptations should remain modular and preserve upstream security contracts. Institutions are encouraged to contribute generally useful improvements upstream.

## Compatibility and releases

The project currently follows a pragmatic release model rather than a formal semantic-version compatibility guarantee. `CHANGELOG.md`, Git tags/commits, migration history, and production-acceptance documents are the authoritative change evidence. Breaking changes should be called out explicitly.

## Governance changes

Material changes to this governance model should be proposed in a pull request and explained in the repository history.
