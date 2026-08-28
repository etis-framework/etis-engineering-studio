# Acceptance Criteria

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This file contains sample acceptance criteria showing how requirements can
be translated into observable, verifiable conditions.

Replace the sample criteria with acceptance criteria for your team's actual
requirements.

Keep identifiers and requirement references consistent with:

/docs/requirements/requirements.md

Acceptance criteria define the observable conditions that demonstrate whether
a requirement has been satisfied.

Remove instructional comments like this one as you complete the artifact.
-->

## Acceptance Criteria

<!--
Replace the sample rows below with your team's actual acceptance criteria.

Recommended identifier format:

AC-REQ-###-##

Examples:
AC-REQ-001-01
AC-REQ-001-02
AC-REQ-002-01

A single requirement may have multiple acceptance criteria.
-->

| ID | Requirement Reference | Acceptance Criterion | Verification Method | Status |
|---|---|---|---|---|
| AC-REQ-001-01 | REQ-001 | Given an authenticated student and valid required information, when the student submits a workflow request, then the system creates the request and assigns it a unique identifier. | Automated test / demonstration | Proposed |
| AC-REQ-001-02 | REQ-001 | Given an authenticated student whose submission is missing required information, when the student attempts to submit the request, then the system rejects the submission and identifies the missing information. | Automated test / demonstration | Proposed |
| AC-REQ-002-01 | REQ-002 | Given an authenticated requester with an existing workflow request, when the requester views their requests, then the system displays the current status of that request. | Automated test / demonstration | Proposed |

<!--
DELETE THE SAMPLE ROWS ABOVE after your team has replaced them with actual
project acceptance criteria.
-->

## Writing Acceptance Criteria

<!--
Acceptance criteria should describe observable behavior or measurable outcomes.

When useful, use:

Given <starting condition>
When <action or event>
Then <observable result>

Given / When / Then is encouraged when it improves clarity, but it is not
mandatory. Another precise formulation is acceptable.

The important requirement is that the criterion be specific and verifiable.

Avoid criteria that merely repeat the requirement without defining how
satisfaction could be observed.
-->

## Positive and Negative Conditions

<!--
Do not consider only the successful path.

For relevant requirements, consider behavior involving:

- missing input;
- invalid input;
- unauthorized access;
- duplicate operations;
- unavailable dependencies;
- boundary conditions;
- failure conditions;
- recovery behavior; and
- other meaningful exceptions.

Not every requirement needs every type of condition. Use engineering judgment.
-->

## Verification Method

<!--
Identify how the team currently expects to demonstrate satisfaction of each
criterion.

Possible methods include:

- automated unit test;
- automated integration test;
- automated end-to-end test;
- manual demonstration;
- inspection;
- analysis;
- code review; or
- operational observation.

At an early phase gate, the method may be preliminary.

As implementation matures, replace general descriptions with concrete,
repository-visible evidence where practical.

Example early reference:
Automated test / demonstration

Example later reference:
tests/integration/test_request_submission.py
-->

## Status Guidance

<!--
Recommended status values:

Proposed
- Criterion has been identified but is not yet part of the accepted baseline.

Accepted
- Criterion is part of the current requirements baseline.

Implemented
- Intended system behavior exists.

Verified
- Evidence demonstrates that the criterion is satisfied.

Failed
- Verification demonstrates that the criterion is not currently satisfied.

Deferred
- Criterion has intentionally been postponed.

Removed
- Criterion no longer applies, but is retained when needed for traceability.

Do not mark a criterion Verified simply because implementation exists.
Verification requires evidence.
-->

## Acceptance Criteria and Implementation Tasks

<!--
Acceptance criteria describe acceptable SYSTEM BEHAVIOR.

They are not implementation tasks.

Acceptance criterion example:

"Given an invalid workflow request, when submission is attempted, then the
request is rejected and the missing required fields are identified."

Implementation-task example:

"Add validation logic to the request controller."

The first defines an observable outcome.
The second describes engineering work.
-->

## Traceability

<!--
Acceptance criteria should eventually connect requirements to verification
evidence.

A mature traceability path may look like:

REQ-001
  ->
AC-REQ-001-01
  ->
Automated integration test
  ->
Implementation
  ->
Phase-gate evidence

Maintain the relationships throughout the project rather than attempting to
reconstruct them at the end.
-->

## Unresolved Criteria

<!--
If the team cannot define a meaningful acceptance criterion because important
information is unknown, do not invent precision.

Record the unresolved matter in:

/docs/requirements/assumptions-open-questions.md

Refine the criterion when the required information becomes available.
-->

## Expectations

- Maintain unique acceptance-criteria identifiers.
- Reference valid requirement IDs.
- Keep requirement-to-criterion traceability current in both files.
- Make criteria observable and verifiable.
- Include important success and failure conditions.
- Identify an appropriate verification method.
- Strengthen verification references as implementation matures.
- Do not claim verification without evidence.
- Record unresolved questions rather than inventing missing behavior.
- Preserve meaningful traceability when criteria change.

<!--
Acceptance criteria are living engineering evidence and should mature alongside
requirements, implementation, and verification.

Before the applicable phase-gate submission:
1. Replace all sample data.
2. Confirm all requirement references are valid.
3. Review criteria for verifiability.
4. Remove instructional HTML comments.
-->
