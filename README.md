# ETIS Engineering Studio

A browser-based engineering judgment environment for COMP 330 that turns phase-gate evidence into interactive, multi-perspective engineering reviews.

The Studio is intentionally **not** a grading bot, passive dashboard, generic chatbot, or artifact generator. It is a structured practice environment in which students must make and defend engineering decisions against evidence, tradeoffs, uncertainty, business constraints, and professional accountability.

## Wave 1

Wave 1 is production-oriented around **Assignment 1 (Project Launch)** and **Assignment 2 (Planning & Estimation)**, while preserving extension contracts for A3-A6.

Implemented in this package:

- A1-A6 machine-readable phase contracts, with detailed A1/A2 review logic.
- Phase-aware repository intelligence with frozen evidence snapshots, starter-kit provenance, FACT/REVIEW separation, and challenge ranking.
- Multi-lens reviewer architecture with strengths-first, repository-driven challenge selection and semantic coaching.
- OpenAI Responses API semantic reviewer conversation plus optional semantic repository interpretation behind bounded provider interfaces.
- A sophisticated student Engineering Review Room UI.
- Instructor Command Center UI.
- Loyola Microsoft Entra SSO for institutional authentication, roster-based semester authorization, and one-time GitHub identity linking.
- Team-level GitHub App repository access with short-lived installation tokens, one-time repository onboarding, and read-only evidence acquisition.
- Multi-term / multi-section semester administration with instructor-controlled roster, teams, release calendar, staff roles, and archival state.
- Role-scoped teaching-staff authorization: Course Owner, Instructor, TA, and Reviewer privileges remain distinct.
- SQLite local development and PostgreSQL-compatible persistence.
- Docker Compose local environment.
- Azure Container Apps / PostgreSQL / Key Vault architecture specification and starter Bicep.
- GitHub Actions CI and Azure deployment workflow starter.
- Automated backend tests.
- Seed/demo mode plus an untouched COMP 330 starter-kit acceptance fixture for repository-intelligence regression testing.

## Core design principle

> AI may challenge, critique, synthesize, and ask for evidence. Engineers decide, defend, and own the consequences.

## Quick start (demo mode)

```bash
cp .env.example .env
# When applying the v0.11 overlay, merge the new identity/integration keys from
# ENV_EXAMPLE_v0.11.0.txt into .env before production-authentication testing.
python -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
uvicorn apps.api.app.main:app --reload --port 8000
```

Open `http://localhost:8000`.

For a full split frontend/backend developer workflow, see `docs/LOCAL_DEVELOPMENT.md`.

## Repository structure

```text
apps/api/                 FastAPI application and agent orchestration
apps/web/                 React/Vite student + instructor UI
course-model/             Machine-readable COMP 330 phase contracts
infra/azure/              Azure deployment starter (Bicep + notes)
docs/                     Architecture, security, product, operations, source model
scripts/                  Development and validation helpers
tests/                    Backend contract and challenge-engine tests
```

## v0.11 identity, course administration, team onboarding, and phase-gated review architecture

A review now follows this control path:

```text
GitHub repository
    ↓
Frozen phase evidence snapshot (FACT)
    ↓
Starter-kit provenance + phase-aware evidence intelligence
    ↓
Reusable compact evidence package (only relevant context)
    ↓
Deterministic + semantic engineering findings (REVIEW)
    ↓
High-value challenge ranking
    ↓
Natural senior-reviewer coaching + rescue/teach-back
    ↓
Learning state, evidence disputes, recorded recommendation, review history
    ↓
Token / latency / estimated-cost telemetry
```

### Identity and course-control model

```text
Loyola Microsoft SSO  -> authenticates the person
Semester roster       -> authorizes active student access
Section staff roles   -> authorize Course Owner / Instructor / TA / Reviewer privileges
GitHub identity link  -> maps the engineer to GitHub once
GitHub App            -> reads the team private repository once connected

Course Template -> Term -> Section -> Team -> Student
                         |
                         +-> section-specific phase calendar / release overrides
```

Students do not receive Studio passwords. The first teammate who reaches an unconnected team can identify the team repository; once verified, every teammate inherits the shared repository connection. Team evidence is shared while review conversations and learning state remain individual.

Student-facing coaching uses the strongest configured model while bounded repository interpretation and the selective conversation critic can be routed to lower-cost models. The instructor surface tracks input, cached input, output, latency, and estimated cost by team without interrupting a student mid-review.

Conversation quality is treated as a release-tested capability. `evals/student_behavior_cases.json` contains novice and outlier cases (tentative wording, typos, slang, non-native English, frustration, hostility, evidence disputes, grading-game requests, misconceptions, answer seeking, and more). Run `python scripts/run_conversation_evals.py` only when an OpenAI key is configured and you intentionally want a paid live semantic smoke-eval.

Use `python scripts/analyze_local_repo.py /path/to/repository --phase A1` to inspect the deterministic repository-intelligence layer without GitHub or model access. See `docs/architecture/REPOSITORY_INTELLIGENCE_AND_REVIEW_ORCHESTRATION.md` for the full design.

## Status

This is a **professional Wave 1 foundation**, not a finished SaaS release. The core product model, server, demo experience, API contracts, repository/evidence abstraction, agent orchestration, access model, and deployment architecture are implemented. Production rollout still requires GitHub OAuth/App registration, Azure resource creation, secrets, DNS, and an OpenAI API key/model selection.

## v0.13 Review Room release-candidate changes

- One primary Start Review control with coherent Board / Focused / Finding review setup.
- Restored and regression-tested live conversation controls after the v0.12 front-end state regression.
- Expanded multilingual/international-student coaching and adversarial/outlier behavior handling.
- Role-aware teaching-staff Help and staff war-game coverage.
- Evidence can be questioned directly from the in-scope Evidence Rail.

See `PATCH_NOTES_v0.13.0.md` and `docs/architecture/REVIEW_ROOM_RELEASE_CANDIDATE.md`.

## v0.14 Engineering Evidence & Review Continuity

The student-facing evidence surface is now an interactive **Engineering Evidence** workspace rather than a glossary of judgment lenses. It shows evidence-supported strengths, current-phase evidence, equivalent/project-specific evidence, snapshot-bound REVIEW findings, and bounded traceability signals. Students can move directly from an artifact, lens, or finding into a Focused or Finding Review without losing the shared frozen evidence baseline.

Focused Review is deliberately consultative: a student can bring work-in-progress to a senior reviewer and ask for a candid professional opinion before moving to the next topic. Reviewers should identify what is already defensible, what remains weak or uncertain, and the highest-value improvement—then coach rather than wait for a failure. Finding Reviews remain about understanding/challenging/resolving an existing REVIEW interpretation, while Board Review remains the normal phase-gate apprenticeship experience.

The user-facing decision action is now **State My Recommendation**. Not every review needs a recommendation; Finding Reviews never force one, and Focused Reviews surface it only when a consequential decision is actually being made.

See `PATCH_NOTES_v0.14.0.md` and `docs/architecture/ENGINEERING_EVIDENCE_AND_REVIEW_CONTINUITY.md`.

## v0.15 Interaction Integrity & Pre-Azure Product Hardening

v0.15 changes the release criterion from “the control exists” to **“the user action produces the exact intended product behavior end to end.”** Finding/evidence actions now preserve stable context into the Review Room, frozen-artifact links are validated rather than guessed, prior sessions have an explicit escape to a clean new-review home, drafts survive failed turns and refreshes, and teaching-staff surfaces degrade with visible retry paths rather than silent failures.

The reviewer engine continues to evaluate engineering meaning independently of English fluency. UI-selected findings/evidence are now explicit semantic context, so phrases such as “this,” “it,” or culturally/non-native-English descriptions remain anchored to what the student selected rather than drifting to an unrelated repository concern.

Browser-level product war games can be run in a developer environment with Playwright/Chromium:

```bash
python scripts/run_ui_wargames.py --base-url http://127.0.0.1:8000
```

The script deliberately mocks only conversation responses so the product journey does not spend OpenAI tokens; repository/session behavior still exercises the local Studio API. See `PATCH_NOTES_v0.15.0.md` and `docs/architecture/INTERACTION_INTEGRITY_AND_PRODUCT_HARDENING.md`.
