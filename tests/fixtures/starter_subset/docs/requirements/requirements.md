# Requirements

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This file contains sample requirements showing the expected structure and
level of detail.

Replace the sample requirements with requirements for your team's actual
system. Do not simply change a few words in the examples.

Requirements describe what the system is obligated to do or satisfy.
They should be clear enough that another engineer can understand the
obligation and determine whether it has been met.

Keep the document structure that is useful to your team, but remove
instructional comments like this one as you complete the artifact.
-->

## Requirements

<!--
Replace the sample rows below with your team's actual requirements.

Use unique IDs in the form REQ-###.

Requirement:
State the system obligation clearly and precisely. When practical, use
"The system shall..." Avoid vague statements such as "The system should
be easy to use" unless the expectation is made observable or measurable.

Rationale:
Explain why the requirement exists. Do not simply restate the requirement.

Priority:
Use Must, Should, or Could.

Acceptance Criteria Reference:
Reference the criteria in acceptance-criteria.md that demonstrate whether
the requirement has been satisfied.

Status:
Recommended values are Proposed, Accepted, Changed, Deferred, or Removed.
-->

| ID | Requirement | Rationale | Priority | Acceptance Criteria Reference | Status |
|---|---|---|---|---|---|
| REQ-001 | The system shall allow an authenticated student to submit a workflow request containing all information required for processing. | Students need a controlled and traceable way to initiate a workflow. | Must | AC-REQ-001-01, AC-REQ-001-02 | Proposed |
| REQ-002 | The system shall allow a requester to view the current status of each workflow request they submitted. | Requesters need visibility into workflow progress without relying on manual status inquiries. | Must | AC-REQ-002-01 | Proposed |

<!--
DELETE THE SAMPLE ROWS ABOVE after your team has replaced them with actual
project requirements.

Do not reuse a requirement ID for a different requirement after that ID has
been referenced elsewhere in the repository.
-->

## Requirement Quality

<!--
Use this section as a final review checklist while developing your requirements.
Delete this comment before submission.

Good requirements should be:

- clear;
- concise;
- unambiguous;
- necessary;
- feasible;
- traceable; and
- verifiable.

Before accepting a requirement, consider:

- What stakeholder, engineering, operational, or project need does it address?
- Is the obligation clear?
- Could two reasonable people interpret it differently?
- Can the team eventually demonstrate whether it has been satisfied?
- Does it unnecessarily prescribe a technical solution?
- Is it consistent with other requirements?
- Does it depend on an unresolved assumption or open question?
-->

## Requirements and Design

<!--
Requirements normally describe WHAT must be true, not unnecessarily dictate
HOW the system must be implemented.

Example of an appropriate requirement:

"The system shall preserve an audit record of workflow status changes."

This establishes an obligation.

By contrast:

"The system shall use PostgreSQL table workflow_history with three indexes..."

is usually an architecture or implementation decision unless that technology
is itself an externally imposed requirement.

Record significant implementation choices in the appropriate architecture or
decision artifact.
-->

## Requirements and Uncertainty

<!--
Do not invent an answer simply because a requirement is incomplete.

If an important fact is unknown, record it in:

/docs/requirements/assumptions-open-questions.md

A known uncertainty is stronger engineering evidence than an unsupported
assumption disguised as a requirement.
-->

## Requirements and Acceptance Criteria

<!--
A requirement establishes an obligation.

An acceptance criterion defines an observable condition demonstrating that
the obligation has been satisfied.

Example:

Requirement:
"The system shall allow a requester to view the current status of each
workflow request they submitted."

Acceptance criterion:
"Given an authenticated requester with an existing workflow request, when the
requester views their request list, then the current status of that request is
displayed."

Maintain traceability in both directions between requirements and acceptance
criteria.
-->

## Expectations

- Maintain unique requirement identifiers.
- Keep requirements current as understanding changes.
- Use professional engineering language.
- Record rationale rather than simply listing features.
- Assign meaningful priorities.
- Link requirements to acceptance criteria.
- Link related decisions, risks, tests, and other evidence when appropriate.
- Record unresolved uncertainty explicitly rather than inventing details.
- Preserve traceability when accepted requirements change, are deferred, or are removed.

<!--
This is a living requirements baseline, not a one-time document.

Before the applicable phase-gate submission:
1. Replace all sample data.
2. Review the document for accuracy and internal consistency.
3. Remove instructional HTML comments.
-->
