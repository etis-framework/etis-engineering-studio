# AI Use Log

<!--
STARTER KIT GUIDANCE — DELETE BEFORE PHASE-GATE SUBMISSION

This log records SIGNIFICANT AI-assisted engineering activity.

It is not intended to become a transcript of every prompt or routine AI
interaction.

Record AI use when it materially influences implementation, tests,
requirements, architecture, decisions, analysis, documentation, debugging,
verification, or other project evidence.

Replace the sample entries below with your team's actual AI use.

Remove instructional comments like this one as you complete the artifact.
-->

## AI Use

<!--
FIELD GUIDANCE

Date
Use YYYY-MM-DD.

Tool
Identify the AI tool or service used. Include a model/version only when it is
known and materially useful.

Purpose
Briefly explain why AI was used.

Artifact / Activity
Identify the affected repository artifact, engineering activity, issue, PR,
decision, test, or other evidence.

Human Verification
Describe how a team member independently reviewed or verified the relevant
output. Link to ai-verification-notes.md when more detailed verification
evidence exists.

Result / Action
State what the team actually did with the AI output.

Examples:
- Accepted after modification
- Rejected
- Used as analysis input
- Implemented and verified
- Identified defect; fix implemented
- No change made
-->

| Date | Tool | Purpose | Artifact / Activity | Human Verification | Result / Action |
|---|---|---|---|---|---|
| 2026-09-03 | ChatGPT | Identify edge cases for workflow submission | REQ-004 / acceptance criteria | Team reviewed suggestions against current requirements; two cases independently added and reviewed | Used as analysis input; AC-REQ-004-03 and AC-REQ-004-04 added |
| 2026-09-08 | GitHub Copilot | Assist with request-validation implementation | `src/workflow/validation.py` | Code reviewed by Taylor Nguyen; unit and integration tests passed; see AVN-001 | Generated code substantially modified and accepted |
| 2026-09-10 | ChatGPT | Investigate failing duplicate-submission test | Issue #14 / PR #21 | Team reproduced defect independently and verified fix through regression test | Diagnosis partially useful; proposed fix rejected; team implemented alternate fix |

<!--
DELETE THE SAMPLE ROWS ABOVE after your team has replaced them with actual
project AI-use entries.

Do not simply replace names and dates. The samples demonstrate the expected
level of specificity.
-->

## What Should Be Logged?

<!--
Normally log AI use when it materially influences:

- requirements;
- acceptance criteria;
- architecture;
- significant engineering decisions;
- implementation;
- tests;
- debugging;
- security analysis;
- risk analysis;
- operational planning;
- project documentation;
- phase-gate evidence; or
- another authoritative project artifact.

Routine low-impact assistance does not necessarily require an individual entry.

Examples that may NOT require logging:

- spelling correction;
- simple syntax reminders;
- basic concept explanation that does not affect project evidence;
- minor wording assistance;
- routine formatting.

Use engineering judgment. The purpose is meaningful traceability, not
administrative volume.
-->

## Human Verification

<!--
"Reviewed by human" is generally too weak.

State WHAT was actually done.

Weak:
"Reviewed"

Stronger:
"Code reviewed by Morgan Lee; unit tests passed."

Stronger:
"Compared recommendation against OAuth provider documentation and verified
behavior in integration test; see AVN-003."

The verification should be proportional to the risk and consequence of the
AI-assisted work.
-->

## Result / Action

<!--
Do not imply that AI output was automatically accepted.

Useful outcomes include:

Accepted
Accepted after modification
Partially used
Rejected
Used for brainstorming only
Used as analysis input
Implemented and verified
No action taken

Where an AI recommendation was rejected, recording that fact may provide
valuable evidence of human engineering judgment.
-->

## Relationship to Verification Notes

For significant AI-assisted work requiring more detailed verification evidence,
reference an entry in:

`/docs/ai/ai-verification-notes.md`

<!--
Example:

Human Verification:
"Independent tests and documentation comparison completed; see AVN-004."

Not every AI Use Log entry requires a separate verification note.

Use verification notes when the verification itself is important enough to
preserve as engineering evidence.
-->

## Expectations

- Record significant AI-assisted engineering activity.
- Identify the affected artifact or engineering activity.
- Describe meaningful human verification.
- Record what was actually done with the AI output.
- Link detailed verification evidence when appropriate.
- Do not fabricate or reconstruct AI use after the fact merely to make the log appear complete.
- Do not record confidential prompts, credentials, secrets, or protected information.
- Keep entries concise but specific enough to be reviewable.
- Preserve meaningful rejected AI recommendations when they demonstrate engineering judgment.

<!--
Before the applicable phase-gate submission:

1. Remove all sample rows.
2. Confirm significant AI-assisted work is represented.
3. Confirm entries reference actual repository evidence where appropriate.
4. Check that verification descriptions state what humans actually did.
5. Remove instructional HTML comments.

The goal is traceability of meaningful AI influence, not a transcript of
every interaction.
-->
