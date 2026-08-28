# Assumptions and Open Questions

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This file contains sample assumptions and open questions showing how known
uncertainty should be made visible and managed.

Replace the sample entries with your team's actual assumptions and unresolved
questions.

Do not leave important uncertainty buried in conversations, meeting notes, or
undocumented implementation choices.

Remove instructional comments like this one as you complete the artifact.
-->

## Key Distinctions

<!--
Use these definitions while developing this artifact:

ASSUMPTION
Something the team is currently treating as true without sufficient
confirmation.

OPEN QUESTION
Something the team explicitly recognizes that it does not yet know.

REQUIREMENT
An obligation the system must satisfy.

ACCEPTANCE CRITERION
An observable condition demonstrating that a requirement has been satisfied.

Do not turn an assumption into a requirement simply because the team needs
an answer.
-->

## Assumptions

<!--
Replace the sample rows below with your team's actual assumptions.

Use IDs in the form:

ASM-###

Examples:
ASM-001
ASM-002
ASM-003

Track assumptions that could meaningfully affect requirements, architecture,
schedule, verification, security, operations, or other engineering decisions.
-->

| ID | Assumption | Basis | Related Evidence | Impact if Incorrect | Owner | Status |
|---|---|---|---|---|---|---|
| ASM-001 | Students will authenticate using an institution-supported identity provider. | Initial project context | REQ-001 | Authentication architecture and access-control requirements may need to change. | Jordan Smith | Unvalidated |
| ASM-002 | A workflow request will have one current status at a time. | Initial domain interpretation | REQ-002 | The workflow model and status presentation may require redesign. | Morgan Lee | Unvalidated |

<!--
DELETE THE SAMPLE ROWS ABOVE after your team has replaced them with actual
project assumptions.
-->

### Assumption Status

<!--
Recommended values:

Unvalidated
- The team is currently treating the assumption as true but has not confirmed it.

Validated
- Sufficient evidence supports the assumption.

Invalidated
- Evidence demonstrates that the assumption was incorrect.

Superseded
- New information or a formal decision replaced the assumption.

When an assumption is validated or invalidated, update every affected
requirement, decision, risk, plan, architecture artifact, or other evidence.

Do not simply change the status and stop there.
-->

## Open Questions

<!--
Replace the sample rows below with your team's actual open questions.

Use IDs in the form:

Q-###

Examples:
Q-001
Q-002
Q-003

State each uncertainty as a real question so the team can determine when it
has actually been answered.
-->

| ID | Question | Related Evidence | Owner | Needed By | Status / Resolution |
|---|---|---|---|---|---|
| Q-001 | Can a requester cancel a workflow after submission? | REQ-001 | Taylor Nguyen | A2 | Open |
| Q-002 | Who is permitted to view workflow history? | REQ-002 | Casey Patel | A2 | Open |
| Q-003 | How long must completed workflow records be retained? | Requirements / Operations | Riley Chen | A3 | Open |

<!--
DELETE THE SAMPLE ROWS ABOVE after your team has replaced them with actual
project questions.
-->

### Open-Question Guidance

<!--
RELATED EVIDENCE

Identify requirements, acceptance criteria, architecture decisions, risks,
plans, security decisions, operational expectations, or other artifacts that
may be affected by the answer.

OWNER

Assign someone responsible for driving the question toward resolution.
Ownership does not mean that person must solve the question alone.

NEEDED BY

Identify the earliest phase gate or engineering decision that would be
materially affected if the question remained unresolved.

Examples:
A2
A3
Before architecture decision
Before implementation

STATUS / RESOLUTION

Recommended states:
Open
Investigating
Resolved
Deferred

When a question is resolved, record the answer and reference the authoritative
evidence where practical.

Example:

Resolved — Requesters may cancel only while status is Submitted.
See REQ-007 and ADR-003.

Do not erase the original question if it influenced engineering decisions.
-->

## Resolving Assumptions

<!--
When an assumption is validated or invalidated:

1. Record the result.
2. Identify the supporting evidence.
3. Review every requirement, decision, risk, design element, or plan that
   depended on the assumption.
4. Update affected artifacts.
5. Preserve traceability to the original assumption where useful.

Example:

ASM-001
  ->
Authentication capability confirmed
  ->
Authentication requirements refined
  ->
Architecture decision updated
  ->
Acceptance criteria updated

The value is not simply recording the assumption. The value is understanding
what depended on it.
-->

## Resolving Open Questions

<!--
When an open question is answered:

1. Record the resolution.
2. Identify where the authoritative answer now exists.
3. Update affected requirements and other engineering evidence.
4. Preserve the question when it provides useful engineering history.

An answer that exists only in a meeting, text message, or chat does not create
durable repository evidence.
-->

## Managing Unknowns

<!--
"We do not know yet" is an acceptable engineering state.

At an early phase gate, some questions will legitimately remain unresolved.

Do not manufacture certainty simply to make the repository appear complete.

For an unresolved item, the team should be able to explain:

- Why does this matter?
- What could it affect?
- Who owns resolving it?
- When must it be resolved?
- What artifacts will need to change after it is resolved?

That demonstrates engineering control over uncertainty.
-->

## Relationship to Risk

<!--
Some assumptions and open questions create meaningful project risk.

If an unresolved matter could significantly affect:

- scope;
- schedule;
- architecture;
- security;
- data integrity;
- verification;
- deployment;
- operations; or
- stakeholder acceptance;

consider linking it to the project's risk documentation.

An assumption and a risk are not the same thing.

The assumption describes something being treated as true despite uncertainty.

The risk describes a potential consequence and how the team intends to manage it.
-->

## Expectations

- Record important assumptions explicitly.
- Record unresolved matters as clear questions.
- Assign owners.
- Identify affected evidence.
- State the impact of important assumptions being wrong.
- Identify when open questions need resolution.
- Update downstream artifacts when uncertainty is resolved.
- Preserve meaningful history rather than silently overwriting prior understanding.
- Link assumptions and questions to risks when the potential consequence warrants it.
- Never invent certainty simply to make an artifact appear complete.

<!--
As the project matures, this file should become more precise and better
connected to other engineering evidence. It should not merely accumulate
unresolved items.

Before the applicable phase-gate submission:
1. Replace all sample assumptions and questions.
2. Confirm ownership and needed-by dates.
3. Update resolved items and affected downstream evidence.
4. Remove instructional HTML comments.
-->
