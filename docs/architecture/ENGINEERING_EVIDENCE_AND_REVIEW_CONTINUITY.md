# Engineering Evidence and Review Continuity

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

### Finding Review
Conversation about one or a small related set of existing REVIEW interpretations. The student can understand, challenge, resolve, accept/defer, or provide contrary evidence. No formal recommendation is required unless the conversation genuinely reaches a consequential decision.

## Recommendation semantics

**State My Recommendation** records a judgment the student is prepared to defend now. It is not a Git commit, grade submission, or permanent answer. It is contextual and revisable when evidence or reasoning changes.

## Multilingual and novice design

Engineering understanding is evaluated separately from English fluency. Reviewers infer intent from context, reflect plausible interpretations when language is ambiguous, use plain English, introduce professional terminology after understanding is established, and teach directly when productive struggle has ended.
