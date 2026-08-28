# Traceability

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This file provides a project-level view of traceability across engineering
evidence.

Traceability answers questions such as:

- Why does this requirement exist?
- What design or architecture addresses it?
- What implementation realizes it?
- What acceptance criteria define success?
- What test or verification evidence demonstrates that it works?
- What decision influenced the solution?
- What risk affects it?
- What changed when an upstream assumption or requirement changed?

Traceability is NOT merely a list of links.

The goal is to preserve meaningful relationships among engineering artifacts.

Do not attempt to populate every possible relationship at A1.

Traceability should mature as the project matures.

IMPORTANT:

- Everything inside HTML comments is Starter Kit guidance.
- Remove instructional comments before the applicable phase-gate submission.
- Examples are guidance only.
-->

## Requirements Traceability Matrix

<!--
TEAM CONTENT REQUIRED

Use the requirement IDs defined in:

/docs/requirements/requirements.md

Add relationships as evidence becomes available.

At early gates, implementation and verification columns may legitimately be
blank or marked as not yet available.

Do not invent downstream evidence merely to make the matrix look complete.

COLUMN GUIDANCE

Requirement
Authoritative requirement ID.

Acceptance Criteria
Related acceptance-criteria IDs.

Architecture / Design
Relevant component, API contract, ADR, or architecture section.

Implementation
Relevant repository path, module, PR, or other implementation evidence.

Verification
Test, runtime evidence, review, or other proof.

Risk / Assumption
Relevant risk or assumption that materially affects the requirement.

Status
Current overall traceability state.

EXAMPLE ONLY:

| Requirement | Acceptance Criteria | Architecture / Design | Implementation | Verification | Risk / Assumption | Status |
|---|---|---|---|---|---|---|
| REQ-001 | AC-REQ-001-01, AC-REQ-001-02 | API-001, Application Service | Not yet implemented | Not yet available | ASM-001 | In Progress |

DELETE the example and populate the actual table below.
-->

| Requirement | Acceptance Criteria | Architecture / Design | Implementation | Verification | Risk / Assumption | Status |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## Decision Traceability

<!--
TEAM CONTENT REQUIRED FOR SIGNIFICANT ENGINEERING DECISIONS

Reference ADRs from:

/docs/decisions/

Show what influenced a decision and what downstream evidence it affected.

EXAMPLE ONLY:

| Decision | Drivers / Inputs | Affected Architecture / Implementation | Verification / Follow-Up |
|---|---|---|---|
| ADR-001 | REQ-001, R-002 | Application Service structure | Architecture review |

Populate actual decision relationships below.
-->

| Decision | Drivers / Inputs | Affected Architecture / Implementation | Verification / Follow-Up |
|---|---|---|---|
|  |  |  |  |

## Risk and Assumption Traceability

<!--
TEAM CONTENT REQUIRED

Show meaningful relationships from uncertainty to affected engineering work.

Do not duplicate the complete risk register or assumptions file.

Reference the authoritative entries.

EXAMPLE ONLY:

| Risk / Assumption | Affected Evidence | Current Effect / Action |
|---|---|---|
| ASM-001 | REQ-001, ADR-002, API-003 | Authentication design remains dependent on provider validation |

Populate actual relationships below.
-->

| Risk / Assumption | Affected Evidence | Current Effect / Action |
|---|---|---|
|  |  |  |

## Change Impact Traceability

<!--
TEAM CONTENT REQUIRED WHEN MATERIAL CHANGE OCCURS

Traceability becomes especially valuable when something changes.

When a requirement, assumption, decision, or architecture element changes,
record the important downstream evidence reviewed or updated.

A blank table is intentional at project start.

EXAMPLE ONLY:

| Change | Upstream Evidence | Downstream Evidence Reviewed / Updated | Result |
|---|---|---|---|
| Authentication method changed | ASM-001, ADR-002 | REQ-001, API-003, integration tests | Contracts and tests updated |

Do not retain the example.
-->

| Change | Upstream Evidence | Downstream Evidence Reviewed / Updated | Result |
|---|---|---|---|
|  |  |  |  |

## Traceability Gaps

<!--
TEAM CONTENT REQUIRED

A gap is a known missing relationship or evidence link.

It is better to record a real gap than to fabricate evidence.

Examples ONLY:

- REQ-005 has no acceptance criterion yet;
- API-004 has no verification evidence yet;
- ADR-003 affects implementation but the affected module has not been identified;
- requirement implementation exists but traceability has not yet been updated.

Use the table below for actual gaps.
-->

| Gap | Why It Matters | Owner | Planned Resolution | Target Gate |
|---|---|---|---|---|
|  |  |  |  |  |

## Traceability Maintenance

<!--
TEAM CONTENT REQUIRED

Describe how the team keeps traceability current.

A lightweight approach is sufficient.

Possible triggers include:

- requirement change;
- ADR acceptance;
- API contract change;
- PR merge;
- new acceptance criterion;
- completed verification;
- risk materialization;
- phase-gate preparation.

The goal is to maintain traceability during engineering work rather than
reconstructing it immediately before submission.

Replace this comment with the team's actual approach.
-->

<!--
FINAL STARTER KIT CHECK — DELETE BEFORE PHASE-GATE SUBMISSION

Before submission:

1. Confirm every current requirement appears in the traceability matrix.
2. Confirm acceptance-criteria references are valid.
3. Link architecture, implementation, and verification only where evidence exists.
4. Do not fabricate downstream links for unfinished work.
5. Identify meaningful gaps explicitly.
6. Confirm ADR and risk relationships point to authoritative evidence.
7. Record downstream review when an upstream artifact changes materially.
8. Remove ALL instructional HTML comments.

The completed traceability artifact should let a reviewer follow important
engineering relationships backward and forward through the lifecycle.
-->
