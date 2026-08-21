# Engineering Evidence and Review Continuity

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.


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
