# Engineering Evidence and Review Continuity

> **Status:** Current design contract inherited and preserved in v0.18.0; dated acceptance evidence is separate.


## Product model

Engineering Studio has two complementary student surfaces:

- **Engineering Review Room** — the apprenticeship conversation with senior reviewers.
- **Engineering Evidence** — the team's living, phase-aware evidence landscape used to inspect artifacts, findings, strengths, and traceability before or between review sessions.

The Evidence surface is not a folder-completion scorecard. A filename is a discovery hint; engineering meaning and provenance determine whether evidence supports a claim. Equivalent evidence may live in another file or GitHub workflow surface. Future starter-kit scaffold is hidden from current-phase judgment by default.

## Evidence scopes

1. **Phase-expected evidence** — concepts and controls normally expected now.
2. **Repository-discovered relevant evidence** — semantically relevant project-specific or equivalent evidence, including GitHub workflow records.
3. **Review-specific evidence** — the compact bounded package actually placed into a reviewer conversation.

## Review continuity

A frozen repository snapshot is team state. Individual conversations are student state. Multiple sessions against the same commit and phase reuse the same immutable snapshot and therefore the same validated finding corrections/disputes. Starting a new session changes the review purpose, not the underlying evidence truth.

Prior student sessions may shape coaching tone and scaffolding, but do not satisfy the current review's evidence or reasoning obligations automatically.

## Review purposes

### Board Review
Normal phase-gate apprenticeship. The board chooses a high-value challenge from the evidence.

### Focused Review
Student-selected work-in-progress consultation. The senior reviewer gives a candid evidence-grounded opinion, identifies the highest-value improvement, and asks one useful next question. It does not require a defect or formal finding.

### Review Findings
Conversation about one or a small related set of existing REVIEW interpretations. The student can understand, challenge, resolve, accept/defer, or provide contrary evidence. No formal recommendation is required unless the conversation genuinely reaches a consequential decision.

## Recommendation semantics

**Current recommendation** is an optional, revisable decision posture: where the student is leaning now. The reviewer may use it to challenge conditions, ownership, evidence, consequences, and change triggers.

**State My Recommendation** is the later explicit action indicating that the student is prepared to record and defend a more developed engineering position. It is not a Git commit, grade submission, or permanent answer. It remains contextual and may change when evidence or reasoning changes.

Not every review requires a recommendation; Review Findings may be explanatory/corrective and Focused Review may remain exploratory.

## Multilingual and novice design

Engineering understanding is evaluated separately from English fluency. Reviewers infer intent from context, reflect plausible interpretations when language is ambiguous, use plain English, introduce professional terminology after understanding is established, and teach directly when productive struggle has ended.

## v0.18.0 frozen review and evidence UX

Review Room is the conversation home; Engineering Evidence is the saved source notebook. The active review stays bound to its immutable snapshot when saved Evidence is newer. Same-snapshot, newer-saved-snapshot, completed-review and no-active-review states must be explicit. Optional review context is secondary to the current concern and conversation.

Inspect cited source opens the attached frozen artifact; Find supporting evidence performs bounded equivalent-evidence discovery without an exact PATH that would suppress search. Discuss, Challenge and Help me resolve this have distinct purposes. No artifact means no guessed inspectable source; aggregate evidence is not a single artifact. A bounded search is not exhaustive absence evidence.

Only authoritative `corrected` or `resolved` findings are closed. Inspection/search, readiness, recommendations, acceptance of risk, deferral and review completion do not close findings. Later commits cannot change a finding's earlier evidence baseline. Machine-triggered instructions appear as review actions, never as student-authored messages; drafts remain private and survive these actions.

Help, artifact, challenge and exit dialogs contain keyboard focus, make background content inert, handle nested focus, and restore a usable opener. Escape uses the existing close behavior; it never submits/completes and does not cancel an already submitted challenge. See the [keyboard contract](DIALOG_KEYBOARD_ACCESSIBILITY.md) and [release contract](../releases/v0.18.0.md).

`Build my recommendation` selects coaching mode; `Discuss Recommendation` sends the composer message in that mode. `State My Recommendation` is the distinct later action that records a ready position. Current recommendation is the optional, revisable posture; none of these establishes finding closure.
