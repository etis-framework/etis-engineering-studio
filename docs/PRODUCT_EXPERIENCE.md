# Product Experience

> **Status:** v0.18.1 student-journey candidate; accepted production v0.18.0 is recorded separately.

## Student: Engineering Studio

The student navigation centers on:

- **Engineering Studio** — Review Room and review launcher;
- **Engineering Evidence** — frozen evidence, strengths, findings, and evidence-driven actions;
- **Review History** — persisted prior review sessions;
- **My Team** — identity/team/project/repository onboarding state;
- **Help & guidance** — bounded product/course guidance.

The product deliberately makes the next student action explicit without turning the experience into a checklist game.

## My Team and repository setup

My Team displays separate readiness states for:

- institutional identity;
- course/team assignment;
- GitHub identity link;
- verified team repository.

Repository nomination accepts an HTTPS GitHub repository URL. The `.git` suffix is optional. Nomination is only a candidate; it is not trusted evidence until verification succeeds.

For a repository that requires GitHub App authorization, the UI presents two explicit steps:

1. GitHub authorization (completed state shows a check/OPENED state);
2. exact repository verification (ACTION REQUIRED until completed).

The GitHub completion page returns the user to Studio without automatically replacing Step 2. Exact verification remains the security boundary.

## Review launcher

Exactly one purpose is selected before a review:

- **Board Review** — board-selected phase-gate question;
- **Focused Review** — student-selected engineering concern;
- **Review Findings** — work directly with existing findings.

The purpose is locked after the session starts.

## Conversation and recommendation

Students can ask questions at any time and may think aloud before deciding.

**Current recommendation** means “this is where I am leaning right now.” It is optional and revisable. The reviewer uses it to challenge the current decision posture.

**State My Recommendation** means the student is prepared to record/defend a more explicit engineering position. It is not required in every review.

The reviewer should:

- recognize what is already defensible;
- explain why the issue matters;
- ask one manageable high-value question;
- provide progressive help when the student is stuck;
- teach directly when productive struggle has ended, followed by teach-back/application;
- accept disagreement and contrary evidence;
- avoid hidden answer-giving or fabricated certainty.

## Engineering Evidence

The evidence workspace distinguishes:

- present/strong evidence;
- starter-kit scaffold;
- weak/incomplete evidence;
- equivalent/project-specific evidence;
- REVIEW findings;
- current phase scope and provenance.

Evidence coverage is not course completion percentage. Starter-kit scaffold does not earn evidence coverage simply because the file exists.

## Instructor workspace

The Instructor Command Center provides:

- shared **SECTION** context across major instructor views;
- aggregate class engineering intelligence;
- teams and attention signals;
- stable team identification;
- team membership/accountability;
- current evidence summary;
- all active student reviews for a team, identified by student;
- persisted review drill-down;
- Engineering Evidence;
- AI Usage & Cost;
- Semester Setup and Settings & Access.

Gold/amber team status means the team currently has an attention signal; green means no current attention signal.

Teaching-staff read visibility does not grant authority to impersonate student review actions.

## Repository recovery

Students cannot directly replace a verified repository. Authorized staff use **Reset repository onboarding**, which clears current repository onboarding state but preserves historical frozen evidence and review records. The team then follows the normal nomination/authorization/verification path.

## Browser behavior

Meaningful Studio navigation participates in browser Back/Forward history while preserving section/team/review context. Minor UI interactions do not create unnecessary history entries.

## v0.18.0 frozen review and evidence UX

Review Room is the conversation home; Engineering Evidence is the saved source notebook. The active review stays bound to its immutable snapshot when saved Evidence is newer. Same-snapshot, newer-saved-snapshot, completed-review and no-active-review states must be explicit. Optional review context is secondary to the current concern and conversation.

Inspect cited source opens the attached frozen artifact; Find supporting evidence performs bounded equivalent-evidence discovery without an exact PATH that would suppress search. Discuss, Challenge and Help me resolve this have distinct purposes. No artifact means no guessed inspectable source; aggregate evidence is not a single artifact. A bounded search is not exhaustive absence evidence.

Only authoritative `corrected` or `resolved` findings are closed. Inspection/search, readiness, recommendations, acceptance of risk, deferral and review completion do not close findings. Later commits cannot change a finding's earlier evidence baseline. Machine-triggered instructions appear as review actions, never as student-authored messages; drafts remain private and survive these actions.

Help, artifact, challenge and exit dialogs contain keyboard focus, make background content inert, handle nested focus, and restore a usable opener. Escape uses the existing close behavior; it never submits/completes and does not cancel an already submitted challenge. See the [keyboard contract](architecture/DIALOG_KEYBOARD_ACCESSIBILITY.md) and [release contract](releases/v0.18.0.md).

`Build my recommendation` selects coaching mode; `Discuss Recommendation` sends the composer message in that mode. `State My Recommendation` is the distinct later action that records a ready position. Current recommendation is the optional, revisable posture; none of these establishes finding closure.

## v0.18.1 candidate: self-explanatory student journey

- **Two rooms:** Engineering Review Room holds the conversation with the Review Board; Engineering Evidence Room shows the latest saved phase evidence. Students can navigate in either direction without finishing a review.
- **Selected versus open:** The user views only one session at a time; multiple Board Reviews can stay open. Review History exposes open/resumable and finished/read-only sessions and supports browsing older pages.
- **Immutable session evidence:** The selected review displays its frozen phase, commit and snapshot ID. Evidence Room's latest saved phase snapshot may differ; an explicit mismatch warning and original-evidence action protect historical FACT. Multiple sessions can reuse one snapshot if phase/commit are unchanged.
- **State-aware guidance:** First-review instructions do not persist into open/finished conversations. The main student action is obvious, reply and Send remain visible, and finishing preserves the read-only transcript. Unsent drafts belong to their original session context.
- **Help:** Routine navigation help is deterministic and does not incur model calls. Engineering guidance remains a separate reviewer interaction; grades and instructor approval are never inferred from the UI.
- **Local acceptance:** The simulator under tools/ is loopback-only and synthetic. Real student, Entra, GitHub, model, screen-reader and Azure acceptance require separate evidence.
