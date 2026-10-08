# ETIS Engineering Studio — Final Student UI Refinement Candidate

**State:** local review candidate, not released, committed, deployed, or human accepted.
**Frozen naming:** Engineering Review Room; Engineering Evidence Room; Review Board.
**Historical baseline:** Studio v0.18.0. Version and analytical modes intentionally unchanged by this patch. Do not infer Azure configuration from local defaults.

## Intent and source of the work

Two COMP330 students independently encountered problems understanding the relationship between the two rooms and the lifecycle of multiple Board Reviews. The supplied local screenshots also revealed duplicated entry actions in a finished review, visually reassuring evidence-area zeros alongside a separate finding, and a need to verify long-conversation focus and recovery.

This candidate is a **bounded frontend and local-simulator refinement**, building on the previously supplied Two-Room + Multi-Review UI candidate. It does not change analysis prompts, database schema, evidence provenance, authorization, grading, identity verification, reviewer/Workbench code, or mode configuration.

## Changes by student state

| State | Student-facing behavior |
| --- | --- |
| No selected review | One principal Start Board Review action; advanced options still available |
| Open review selected | Current-review card and conversation remain central; hide duplicated first-time setup and quick-start strips; preserve both room tabs, review history and Start another Board Review |
| Finished review selected | Keep finished review selected and read-only; hide misleading Begin with a Board Review panel, duplicate hero and quick-start strips; make Start another Board Review the next primary action |
| Evidence matches selected review | Explicit snapshot and commit context; matches are stated factually |
| Evidence differs from selected review | Visibly distinguish the latest saved phase evidence from the frozen review snapshot; point the student back to original Review Room evidence rail; do not backfill earlier facts |

Navigation and completion remain separate. A student may have several open review **sessions**, view one at a time, finish an old one and preserve the others. Two review sessions may legitimately share a snapshot when phase and commit are unchanged. The student, not the Studio, makes engineering decisions; instructor approval and grades remain separate.

## Evidence labels, not analytics changes

The four categories in the Engineering Evidence summary count **evidence areas by condition**. Review Board findings are separately classified reviewer interpretations and may exist even if the four area-condition counters are zero. The candidate adds a fifth, distinct *Review Board findings* count and a concise explanation. Existing `% expected-evidence coverage` measurements are more explicitly labeled as location/inventory indicators, not completeness, quality, participation, grade, or phase-gate acceptance. No metrics are recalculated or reweighted.

## Navigation and information density

The paired room switcher and snapshot context already establish Evidence Room location, so its redundant secondary “You are here” strip is hidden. In Review Room, a selected-review status card makes first-use reminders redundant; the latter are hidden while a review is selected, but remain reopenable from Help. The reply field, Send button, and current-review selector are preserved.

## Long conversation and safe recovery

A new browser war game exercises 32 long student/reviewer exchange pairs, manual scroll to an early message, a harmless UI update that must not jump the reading position, room switches, snapshot mismatch, and a deliberately lost HTTP acknowledgment after a saved response. On retry, the simulator now honors a logical `client_turn_id`, matching the existing API idempotency design: the identical logical response must not be persisted twice. The user draft is restored after the uncertain first acknowledgement. **This is synthetic test behavior, not proof of real network recovery.**

## Evidence boundaries and authority

- Frozen repository FACT remains immutable for earlier checkpoint snapshots.
- Reviewer interpretations and findings remain challengeable and must not be equated with objective facts.
- Later repository commits cannot retroactively become evidence for an earlier review.
- Shared team evidence does not imply shared private coaching conversations.
- Missing attributable activity does not prove nonparticipation, and grades and individual assessments remain instructor-owned.
- No backend analytical authority, deployment/evaluation mode, or grading changes are authorized by this candidate.

## Testing and evidence categories

### Completed in the isolated candidate environment

- Focused Python regression suite, including A1–A6 / weak-average-strong repositories / no-weak-average-strong attributable-participation matrix.
- Existing mocked Chromium lifecycle and new long-conversation / response-retry browser war game at 1440×900, 1280×650 and 390×844.
- JavaScript and Python syntax checks and deterministic keyboard/dialog state harness.
- Patch replay against the immediately preceding Two-Room + Multi-Review candidate.
- Zero paid-model calls.

### Not completed; must not be claimed as accepted

- Actual authenticated Loyola/Entra session or live student records.
- Actual GitHub repository integration and snapshot capture against a controlled test repository.
- Actual network-outage/server-commit reconciliation (rather than synthetic test response loss).
- Screen-reader acceptance on macOS VoiceOver/other assistive technologies.
- Uncoached student usability acceptance and instructor release approval.
- Azure deployment and any post-deployment monitoring.

## Local human acceptance questions

1. Without Help, explain both rooms and navigate to supporting evidence and back.
2. Identify the currently selected review, whether it is open or read-only, and its frozen snapshot/commit.
3. Start a second Board Review without finishing the first, then return to the first conversation.
4. Confirm a saved phase snapshot may differ from the selected review's evidence.
5. Finish one review, confirm it remains selected and read-only, and verify another open review is unchanged.
6. Confirm the next action is consistent with the review state, and that a long response can be typed, recovered, and submitted without confusion.
7. Explain why four zero evidence-area counts can coexist with a separate Review Board finding.

Do not update student-facing manuals until the interface and wording pass local human acceptance. After that, prepare a complete review → improve → commit/push → new snapshot → new review walkthrough with screenshots of the **accepted** UI.
