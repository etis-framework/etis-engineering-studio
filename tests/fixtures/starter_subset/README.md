# Project Name

<!--
STARTER KIT GUIDANCE — DELETE AFTER INITIAL TEAM SETUP

Replace "Project Name" above with your team's approved project name.

This README is the entry point to your project's engineering record.

Before your first phase-gate submission:

1. Replace the project name.
2. Complete the Project Overview.
3. Confirm the Project Status.
4. Confirm your team information is current in /docs/team/roles.md.
5. Add any prerequisites already known.
6. Add build, run, and test instructions as implementation develops.
7. Remove all Starter Kit instructional HTML comments that no longer provide
   useful team guidance.

Continue updating this README throughout the semester.

The README should orient another engineer to the project. It should NOT
duplicate the detailed authoritative engineering evidence maintained elsewhere
in the repository.
-->

## Project Overview

<!--
TEAM CONTENT REQUIRED

Replace this comment with a concise description of your actual project.

In a few sentences, explain:

- the problem the system addresses;
- its intended users or stakeholders;
- its primary purpose; and
- the major scope of the system.

Keep this at an overview level. Detailed requirements belong under
/docs/requirements/.
-->

## Project Status

**Current Phase Gate:** A1 — Project Launch  
**Release Cycle:** Cycle 1  
**Status:** Active Development

<!--
TEAM GUIDANCE — DELETE WHEN NO LONGER NEEDED

Keep this section current throughout the semester.

Use the current course phase-gate terminology:

- A1 — Project Launch
- A2 — Planning & Requirements
- A3 — Architecture & Design
- A4 — Implementation & Review
- A5 — Verification & Release
- A6 — Operational Maturity

Update Release Cycle and Status as the project progresses.

Do not leave the repository permanently showing A1 after the project has moved
to a later gate.
-->

## Team

The authoritative team roster, GitHub identities, specialized role ownership,
backup responsibilities, and team acknowledgements are maintained in:

[`docs/team/roles.md`](docs/team/roles.md)

<!--
TEAM GUIDANCE — DELETE WHEN NO LONGER NEEDED

Keep /docs/team/roles.md current when:

- team membership changes;
- GitHub identities change;
- specialized roles change;
- evidence ownership changes; or
- backup responsibilities change.

Do not maintain a second competing team roster in this README.
-->

## Engineering Evidence

This repository is the **authoritative engineering record** for the project.

Engineering evidence is maintained throughout the repository:

- **AI Use and Verification** → [`docs/ai/`](docs/ai/)
- **Architecture** → [`docs/architecture/`](docs/architecture/)
- **Engineering Decisions** → [`docs/decisions/`](docs/decisions/)
- **Observability** → [`docs/observability/`](docs/observability/)
- **Operations** → [`docs/operations/`](docs/operations/)
- **Planning and Traceability** → [`docs/planning/`](docs/planning/)
- **Quality and Defects** → [`docs/quality/`](docs/quality/)
- **Release Evidence** → [`docs/release/`](docs/release/)
- **Requirements and Acceptance Criteria** → [`docs/requirements/`](docs/requirements/)
- **Engineering Reviews** → [`docs/review/`](docs/review/)
- **Security and Data Handling** → [`docs/security/`](docs/security/)
- **Team Evidence** → [`docs/team/`](docs/team/)
- **Testing and Verification** → [`docs/testing/`](docs/testing/)

Detailed evidence should remain in its authoritative artifact rather than being
duplicated in this README.

## Repository Structure

The repository is organized to preserve both the software system and the
engineering evidence supporting it.

| Path | Purpose |
|---|---|
| `src/` | Production application source code |
| `tests/` | Executable automated tests and supporting test code |
| `test-evidence/` | Preserved evidence produced by testing and verification |
| `data/` | Repository-managed project, seed, fixture, sample, or reference data |
| `scripts/` | Repeatable development, verification, deployment, or maintenance utilities |
| `docs/` | Lifecycle engineering evidence and documentation |
| `.github/` | Issue templates, pull-request guidance, workflows, and repository automation |

<!--
TEAM GUIDANCE — DELETE WHEN NO LONGER NEEDED

Update this section if your project introduces another top-level directory that
is important to understanding or operating the system.

Do not list every directory in the repository. Focus on major engineering
areas.
-->

## Build, Run, and Test

<!--
TEAM CONTENT REQUIRED AS IMPLEMENTATION DEVELOPS

A new engineer should eventually be able to use this section to:

1. clone the repository;
2. install required dependencies;
3. configure the development environment;
4. build the system;
5. run the system; and
6. execute the automated tests.

Use actual commands and procedures.

Do not invent instructions before the technology stack is selected.

Never place passwords, tokens, private keys, or other secrets in this README.
-->

### Prerequisites

<!--
TEAM CONTENT REQUIRED

Document the software, runtimes, tools, services, and important versions needed
to work with the project.

Examples might include:

- programming-language runtime;
- package manager;
- database;
- container runtime;
- required external service.

Include only prerequisites the project actually uses.
-->

### Setup

<!--
TEAM CONTENT REQUIRED WHEN SETUP IS NEEDED

Document the initial setup steps another engineer must perform after cloning
the repository.

Keep secret values out of the repository.

If configuration requires environment variables or external secret management,
explain the mechanism without including the secret itself.
-->

### Build

<!--
TEAM CONTENT REQUIRED

Document the actual build or preparation procedure.

If the project does not require a separate build step, state that clearly
instead of inventing one.
-->

### Run

<!--
TEAM CONTENT REQUIRED

Document how to start the system and how another engineer can confirm that it
started successfully.

Reference /docs/operations/runbook.md for detailed operational procedures when
appropriate.
-->

### Test

<!--
TEAM CONTENT REQUIRED

Document the normal command or procedure for executing the automated test suite.

Detailed testing strategy, planning, test cases, and CI evidence belong under:

/docs/testing/

Do not duplicate those artifacts here.
-->

## Engineering Practices

This project uses repository-centered engineering practices, including:

- lifecycle-based engineering evidence;
- requirements and acceptance-criteria traceability;
- issue and pull-request workflows;
- documented architecture and engineering decisions;
- automated testing and verification;
- peer review;
- explicit defect and quality management;
- security and data-handling evidence;
- responsible AI-assisted engineering;
- explicit AI disclosure and human verification;
- release-readiness evidence;
- operational and observability evidence; and
- continuous improvement.

Engineering evidence should be created and maintained **as the work occurs**,
not reconstructed only when a phase-gate submission is due.

## Engineering Evidence Model

Important engineering claims should be supported by traceable evidence.

A typical lifecycle relationship may look like:

    Requirement
      ->
    Acceptance Criterion
      ->
    Architecture / Decision
      ->
    Implementation
      ->
    Test / Review
      ->
    Verification Evidence
      ->
    Release Evidence

Not every artifact requires every link.

The goal is meaningful traceability, not paperwork.

When upstream engineering evidence changes, review the downstream evidence that
may be affected rather than allowing artifacts to silently diverge.

## AI-Assisted Engineering

AI may assist engineering work, but it does not replace human engineering
responsibility.

The team remains responsible for understanding, reviewing, verifying, and
defending its work regardless of whether AI contributed to it.

Authoritative AI-use and verification evidence is maintained under:

[`docs/ai/`](docs/ai/)

Significant AI-assisted work should be disclosed and independently reviewed in
accordance with the team's AI policy.

## Engineering Operating Model

COMP 330/474 uses three complementary environments:

- **Sakai** — the authoritative source for required readings, assignments, due
  dates, naming, grading, and submission expectations.
- **ETIS** — the professional engineering reference ecosystem, including the
  ETIS Framework, books and publications, Engineering Platform, and supporting
  guidance.
- **GitHub** — the authoritative engineering record for the team's project,
  decisions, implementation, reviews, testing, and evidence.

**Sakai defines what the course requires.**  
**ETIS provides the broader engineering discipline and professional reference model.**  
**GitHub preserves the evidence of what the team actually engineered.**

## Professional Engineering Expectations

A reviewer examining this repository should be able to determine:

- what the team intends to build;
- what problem the system addresses;
- who owns and contributes to the work;
- what requirements define expected behavior;
- what assumptions and risks remain;
- what engineering decisions were made and why;
- how requirements connect to architecture and implementation;
- what interfaces and responsibility boundaries exist;
- what was reviewed and tested;
- what defects were discovered and how the team responded;
- how AI-assisted work was disclosed and verified;
- how security and data handling were considered;
- what limitations remain;
- whether the current release is supported by verification evidence;
- how the system can be operated and observed; and
- how the project improved over time.

A working system is necessary, but it is not sufficient.

Professional engineering also requires evidence that the system can be
understood, reviewed, governed, changed, verified, operated, and defended.

## Course and Professional Context

This repository was established from the **COMP 330/474 Fall 2026 Repository
Starter Kit** for Software Engineering at Loyola University Chicago.

The Starter Kit establishes the initial repository structure and engineering
evidence model used throughout the course. Each team is responsible for
replacing the initial scaffolding with its own project-specific engineering
evidence as the project develops.

The broader ETIS professional engineering ecosystem is available at:

https://etisframework.org/

Use ETIS as professional guidance and reference material.

**Sakai remains authoritative for COMP 330/474 course requirements.**

<!--
FINAL STARTER KIT README CHECK — DELETE AFTER INITIAL SETUP

Before the first phase-gate submission:

1. Replace "Project Name."
2. Complete Project Overview.
3. Confirm Project Status is current.
4. Confirm /docs/team/roles.md contains the actual team.
5. Add all currently known prerequisites.
6. Add real setup/build/run/test instructions as those capabilities exist.
7. Confirm all repository paths above exist and are correctly named.
8. Remove stale Starter Kit guidance.
9. Do not duplicate authoritative engineering evidence in this README.
10. Remove this final instructional comment.

After setup, continue maintaining the README as the project's engineering
entry point throughout the semester.
-->
