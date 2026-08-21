# ETIS Engineering Studio

ETIS Engineering Studio is an open-source, browser-based **engineering apprenticeship environment** for software engineering education. It turns frozen repository evidence into structured reviews in which students must make, explain, challenge, and defend engineering decisions.

The Studio is intentionally **not** a grading bot, generic chatbot, code generator, or autonomous engineering authority. AI reviewers may challenge, critique, synthesize, coach, and ask for evidence. **Students remain the responsible engineers.**

The project was first developed and production-tested in the Loyola University Chicago COMP 330/474 software engineering context. The public project is intended to support **institutional adoption, adaptation, research, and teaching** beyond that original deployment.

> **Reference deployment status — 2026-08-21:** the ETIS Framework production deployment reached Post-Provisioning Production Acceptance **GO**. That acceptance evidence applies to the reference deployment and does not automatically certify an adopter's independent deployment.

## Why institutions may want ETIS

ETIS is designed for courses where students need to practice engineering judgment rather than merely produce code. It provides a bounded environment for:

- evidence-based design and architecture reviews;
- requirements, construction, verification, and operational-maturity reasoning;
- explicit tradeoff and consequence analysis;
- responsible AI-assisted engineering practice;
- individual accountability inside team-based development;
- instructor visibility without turning the system into an automated grading authority;
- repeatable review history and engineering decision records.

The current implementation is optimized for Microsoft Azure, Microsoft Entra, GitHub, PostgreSQL, and OpenAI. Institutions using different identity, source-control, cloud, or AI providers should treat those integrations as adaptation points rather than assume drop-in compatibility.

## Core design principle

> AI may challenge, critique, synthesize, and ask for evidence. Engineers decide, defend, and own the consequences.

## Current capabilities

- Microsoft Entra authentication with database-derived course authorization.
- Course → Term → Section → Team → Student administration with `setup`, `active`, and `archived` term lifecycle states.
- Section-scoped Course Owner, Instructor, TA, Reviewer, and Student authority.
- Personal GitHub identity linking separated from team-level repository authorization.
- Team repository onboarding with candidate → authorization-required → verified state transitions.
- Personal-repository ownership based on immutable GitHub account ID.
- Organization-repository authorization through GitHub's native GitHub App installation/request flow.
- GitHub App access restricted to **Only select repositories**; `all repositories` fails closed.
- Exact-repository GitHub App installation tokens; no PATs and no retained GitHub OAuth access tokens.
- Frozen repository evidence snapshots with starter-kit provenance and FACT/REVIEW separation.
- Board Review, Focused Review, and Review Findings workflows.
- Persistent review history, finding corrections/dispositions, evidence disputes, and team-level review memory.
- OpenAI-backed semantic coaching with deterministic control, model routing, token/latency/cost telemetry, and selective critic behavior.
- Instructor Command Center with section context, team/evidence/review visibility, AI economics, semester setup, and bounded recovery actions.
- Azure reference architecture using Container Apps, private PostgreSQL Flexible Server, Key Vault, managed identity, ACR, Application Insights, Log Analytics, alerts, PITR, and immutable-image rollback.

## Student review model

```text
Verified team repository
    ↓
Frozen phase evidence snapshot (FACT)
    ↓
Phase-aware evidence intelligence
    ↓
Bounded evidence package
    ↓
Deterministic + semantic engineering findings (REVIEW)
    ↓
Board / Focused / Review Findings purpose
    ↓
Senior-reviewer coaching and challenge
    ↓
Student recommendation, evidence dispute, correction, or review completion
    ↓
Persistent learning/review record + AI usage telemetry
```

Exactly one review purpose is active for a review session:

- **Board Review** — normal phase-gate review; the board selects the highest-value current issue.
- **Focused Review** — student-selected work-in-progress, decision, artifact, architecture concern, risk, pull request, AI-use question, or other engineering subject.
- **Review Findings** — understand, challenge, resolve, accept, defer, or provide contrary evidence for existing REVIEW findings.

Review type is selected before the session and remains fixed during that session. Frozen evidence is immutable; validated REVIEW interpretations may be corrected without rewriting the frozen evidence.

## Identity and repository authority

```text
Institutional identity   authenticates the Studio user
Course/term/section      grants current course authority
Team membership          grants current team authority
GitHub identity link     identifies the user's GitHub account
GitHub App               grants repository evidence access
Verified repository      becomes shared team evidence authority
```

A typed repository URL is only a **candidate**. It does not become authoritative team evidence until ETIS verifies the exact repository.

```text
No repository
  → Candidate repository
  → Owner authorization required
  → Verified team repository
```

Students cannot directly replace a verified repository. A Course Owner/Instructor can reset repository onboarding, after which the team follows the normal nomination and verification path again. Historical frozen evidence and review records remain intact.

## Institutional adoption

Start with [`docs/INSTITUTIONAL_ADOPTION.md`](docs/INSTITUTIONAL_ADOPTION.md). An adopting institution should provision and own its own:

- cloud subscription/resources;
- institutional identity registration/tenant configuration;
- GitHub App and OAuth registration;
- DNS/domain and TLS configuration;
- PostgreSQL database and backup policy;
- Key Vault/secrets;
- OpenAI project/API credentials and cost controls;
- course terms, sections, teams, and retention decisions.

**Do not copy ETIS Framework production identifiers, secrets, tenant values, GitHub App credentials, or acceptance-test identities into another institution's deployment.**

Before exposing a deployment to students, follow [`docs/PUBLIC_DEPLOYMENT_SECURITY.md`](docs/PUBLIC_DEPLOYMENT_SECURITY.md) and run an institution-specific production acceptance campaign.

## Local development

The deployable Wave 1 UI is served directly by FastAPI from `apps/api/app/static/`; Node.js is not required for the normal local developer path.

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
uvicorn apps.api.app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

Production configuration is fail-closed and must not be copied into local `.env` files. See [`docs/LOCAL_DEVELOPMENT.md`](docs/LOCAL_DEVELOPMENT.md).

## Repository map

```text
apps/api/                 FastAPI application, services, routes, and deployed static UI
apps/web/                 Reserved React/Vite source area; not the current production UI
course-model/             Machine-readable course phase contracts and source model
infra/azure/              Source-controlled Azure Bicep reference deployment
.github/workflows/         CI and protected manual Azure deployment workflows
docs/                     Architecture, security, product, adoption, operations, and acceptance
evals/                    Student/staff/UI behavioral regression corpora
scripts/                  Development, validation, evaluation, and recovery helpers
tests/                    Automated application/security/operations regression suite
```

## Documentation

Start with [`docs/README.md`](docs/README.md). Important public/adoption documents include:

- [`docs/INSTITUTIONAL_ADOPTION.md`](docs/INSTITUTIONAL_ADOPTION.md) — institutional planning and adoption path.
- [`docs/PUBLIC_DEPLOYMENT_SECURITY.md`](docs/PUBLIC_DEPLOYMENT_SECURITY.md) — security checklist for independent deployments.
- [`docs/PUBLIC_RELEASE_CHECKLIST.md`](docs/PUBLIC_RELEASE_CHECKLIST.md) — repository-publication checklist for maintainers.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — architecture and trust boundaries.
- [`docs/AZURE_DEPLOYMENT.md`](docs/AZURE_DEPLOYMENT.md) — Azure/GitHub/Entra reference deployment.
- [`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md) — security, privacy, retention, and semester lifecycle.
- [`docs/PRODUCTION_BASELINE.md`](docs/PRODUCTION_BASELINE.md) — evidence from the ETIS Framework reference deployment.
- [`BUILD_REPORT.md`](BUILD_REPORT.md) — reference production build and validation record.
- [`CHANGELOG.md`](CHANGELOG.md) — consolidated release history.

## Contributing and community

Contributions are welcome when they preserve the project's educational and security invariants. See:

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`GOVERNANCE.md`](GOVERNANCE.md)
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- [`SECURITY.md`](SECURITY.md)
- [`SUPPORT.md`](SUPPORT.md)

Security vulnerabilities should **not** be reported in public issues. See `SECURITY.md`.

## License

ETIS Engineering Studio is licensed under the **Apache License, Version 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). The license permits institutional use, modification, and redistribution subject to its terms, including preservation of required notices.

The Apache license does not grant trademark rights. See [`TRADEMARKS.md`](TRADEMARKS.md).

## Citation

Academic and institutional users may cite the project using [`CITATION.cff`](CITATION.cff).

## Reference deployment note

The production host and acceptance evidence documented in this repository describe the ETIS Framework reference deployment. They are useful engineering evidence, not a guarantee that an independent deployment is secure, compliant, available, or production-ready. Every adopting institution remains responsible for its own identity, privacy, accessibility, security, retention, legal, procurement, AI-governance, and operational requirements.
