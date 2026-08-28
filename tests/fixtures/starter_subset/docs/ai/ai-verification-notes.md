# AI Verification Notes

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This file records detailed verification evidence for significant AI-assisted
engineering work when the short Human Verification field in ai-use-log.md is
not sufficient.

Not every AI interaction requires a verification note.

Create an entry when the AI-assisted work has enough engineering significance,
risk, or downstream impact that the verification itself should be preserved
as reviewable evidence.

Replace the sample entry below with actual project evidence.

Remove instructional comments like this one as you complete the artifact.
-->

## Verification Notes

<!--
Use unique IDs in the form:

AVN-###

Examples:
AVN-001
AVN-002
AVN-003

Reference these IDs from /docs/ai/ai-use-log.md when appropriate.
-->

### AVN-001 — Request Validation Implementation

**Date:** 2026-09-08  
**AI Tool:** GitHub Copilot  
**Related AI Use Log Entry:** 2026-09-08  
**Related Evidence:** `REQ-004`, `AC-REQ-004-01`, `src/workflow/validation.py`

#### AI Contribution

Copilot generated an initial implementation of request-field validation and
suggested handling for missing required fields.

#### Human Verification Performed

Taylor Nguyen reviewed the generated implementation line by line and compared
its behavior with `REQ-004` and the related acceptance criteria.

The team identified that the initial generated implementation did not correctly
handle whitespace-only values. The implementation was modified before merge.

Verification included:

- code review;
- existing unit tests;
- an additional whitespace-only input test;
- integration testing of valid and invalid submissions; and
- review of the resulting error response against the acceptance criteria.

#### Result

The original AI-generated implementation was not accepted unchanged.

The corrected implementation passed the relevant unit and integration tests and
was accepted through the team's normal pull-request process.

#### Remaining Concerns

No known unresolved concerns related to this AI contribution remain.

<!--
DELETE THE SAMPLE AVN-001 ENTRY ABOVE after your team has created actual
verification evidence.

The sample demonstrates the expected structure and level of detail.
-->

---

<!--
COPY THE TEMPLATE BELOW for each significant verification note.

### AVN-### — Short Descriptive Title

**Date:** YYYY-MM-DD
**AI Tool:**
**Related AI Use Log Entry:**
**Related Evidence:**

#### AI Contribution

Describe what AI materially contributed.

Do not paste an entire AI conversation unless there is an exceptional reason
to preserve it. Summarize the engineering-relevant contribution.

#### Human Verification Performed

Describe specifically how humans independently evaluated the work.

Possible evidence might include:

- code review;
- unit testing;
- integration testing;
- end-to-end testing;
- manual reproduction;
- comparison with requirements;
- comparison with acceptance criteria;
- comparison with authoritative technical documentation;
- security review;
- architecture review;
- independent calculation or analysis;
- runtime observation;
- peer review.

Do not simply state "verified" or "reviewed."

#### Result

State what happened after verification.

Examples:

- accepted unchanged;
- accepted after modification;
- partially accepted;
- rejected;
- replaced with another approach;
- additional requirements identified;
- defect found and corrected;
- further investigation required.

#### Remaining Concerns

Identify unresolved uncertainty, risk, limitations, or follow-up work.

If none are known, state that explicitly.

---
-->

## When to Create a Verification Note

<!--
A separate verification note is especially useful when AI materially
contributes to:

- security-sensitive code;
- authentication or authorization;
- data integrity logic;
- significant architectural decisions;
- complex algorithms;
- concurrency or transaction handling;
- deployment or operational behavior;
- substantial requirements analysis;
- important test design;
- defect diagnosis with significant downstream impact;
- phase-gate evidence;
- other work where an unsupported AI error could have meaningful consequences.

A separate note is usually unnecessary for trivial or low-risk AI assistance.
-->

## Verification Independence

<!--
Verification should not simply ask the same AI system whether its prior answer
was correct.

AI may assist in verification, but meaningful verification should include
independent human judgment and appropriate external evidence.

For example:

WEAK:
"ChatGPT generated the code and then said the code was correct."

STRONGER:
"Team member reviewed the code against REQ-006, added boundary-condition tests,
ran the integration suite, and compared library behavior against authoritative
documentation."

The purpose is independent engineering evidence.
-->

## Verification Depth

The depth of verification should be proportional to the potential consequence
of accepting incorrect AI output.

<!--
Examples:

LOW CONSEQUENCE
AI rewrites a documentation sentence.
Verification might be ordinary human proofreading.

MODERATE CONSEQUENCE
AI generates routine transformation logic.
Verification might include code review and automated tests.

HIGH CONSEQUENCE
AI generates authentication, authorization, data-integrity, concurrency, or
deployment logic.
Verification should include stronger independent review, relevant testing,
and other appropriate evidence.

Do not mechanically apply the same verification process to every AI use.
Exercise engineering judgment.
-->

## Verification Against Requirements

Where AI-assisted work implements or affects system behavior, verification
should reference the applicable requirements and acceptance criteria when
practical.

<!--
A useful evidence chain is:

AI Use Log Entry
  ->
AI Verification Note
  ->
Requirement / Acceptance Criterion
  ->
Implementation
  ->
Test / Review Evidence

Not every activity requires every link, but important AI-assisted engineering
work should be traceable into the same evidence system as other engineering
work.
-->

## Failed Verification Is Valuable Evidence

<!--
Do not hide AI-generated work that fails verification.

A failed verification may demonstrate excellent engineering judgment.

Example:

AI recommendation
  ->
Independent verification
  ->
Defect or unsupported assumption discovered
  ->
Recommendation rejected
  ->
Correct approach implemented

Record the result when the failure is significant enough to affect project
history or engineering decisions.
-->

## Expectations

- Create verification notes for significant AI-assisted work when detailed evidence is warranted.
- Use unique `AVN-###` identifiers.
- Link entries to the AI Use Log and related engineering evidence.
- Describe the AI contribution accurately.
- Describe what humans actually did to verify it.
- Use verification methods appropriate to the potential consequence.
- Record modifications, rejection, or failed verification honestly.
- Identify remaining uncertainty or risk.
- Do not treat AI self-confirmation as sufficient independent verification.
- Keep evidence concise enough to review while preserving important engineering reasoning.

<!--
Before the applicable phase-gate submission:

1. Delete the sample AVN-001 entry.
2. Confirm all retained notes correspond to actual project AI-assisted work.
3. Confirm links and evidence references are valid.
4. Confirm verification descriptions identify actual human actions.
5. Remove instructional HTML comments.

This file is engineering evidence of HOW the team established confidence in
significant AI-assisted work, not evidence that AI was used.
-->
