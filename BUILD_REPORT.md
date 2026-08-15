# Wave 1 Build Report

## Built

- Running FastAPI application with embedded professional student/instructor UI.
- Machine-readable A1-A6 course model; detailed A1/A2 contracts and scenarios.
- Sakai operational metadata for A1-A6.
- Deterministic review/challenge control plane.
- Optional bounded OpenAI Responses API follow-up provider.
- GitHub read-only evidence provider (token-backed developer implementation; GitHub App is the production target).
- Persistent user/team/evidence/review data model.
- Development login and seeded mixed-evidence demo.
- Instructor overview foundation.
- Docker/PostgreSQL local environment.
- Azure Bicep starter and GitHub Actions CI/deploy starter.
- Architecture, product, security/privacy, deployment, acceptance, and next-build documentation.

## Verified in this build

- `pytest`: 8 tests passed.
- Course-model validator passed.
- Python compilation passed.
- Live API health smoke test passed.
- A1-A6 phase endpoint smoke test passed.
- Embedded Engineering Review Room HTML smoke test passed.

## Deliberately not represented as complete

- Production GitHub App installation-token flow and roster administration UI.
- Production-grade secure session/CSRF/rate-limit middleware.
- Deep GitHub evidence ingestion (PR reviews, Actions/check runs, tags/releases, selected Markdown semantic extraction).
- Full A3-A6 conversational/scenario depth.
- Final Azure resource provisioning, DNS, secrets, budgets, backups, and production acceptance testing.
- Confidential peer-review ingestion; intentionally separated until an instructor-only privacy design is completed.
- Autonomous grading; intentionally out of scope.

The build is intentionally honest about these boundaries: Wave 1 should be valuable and defensible, not create the appearance of a finished SaaS before production controls exist.
