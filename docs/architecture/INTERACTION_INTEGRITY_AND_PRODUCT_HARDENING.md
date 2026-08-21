# Interaction Integrity and Product Hardening

> **Status:** Current design contract within the production-accepted 2026-08-21 baseline.


## Purpose

v0.15 treats ETIS Engineering Studio as a product rather than a collection of features. The release criterion is not that a control renders or an API endpoint responds; the criterion is that an authorized user can take an action and the system preserves the exact intent, evidence context, permissions, and navigation state end to end.

## Product contract

Every actionable surface must answer five questions without requiring knowledge of the Studio implementation:

1. Where am I?
2. What am I looking at?
3. What can I do?
4. What will happen if I do it?
5. What should I do next?

A visible control may not be inert. If an action is unavailable, it must be disabled and explain why. A failed asynchronous operation must preserve the user's work and offer a recovery path.

## Context integrity

Contextual actions carry stable identifiers rather than reconstructing intent from the destination screen.

A review handoff can include:

- course / term / section / team identity;
- immutable evidence snapshot;
- review session;
- finding identifier;
- evidence path / evidence reference;
- review mode;
- entry intent (`discuss`, `challenge`, `resolve`, `understand`, `accept_or_defer`);
- source view.

For example, selecting **Help me resolve this** on an estimates finding must create a Review Findings session anchored to that exact estimates finding. The board may broaden the discussion only when the student intentionally changes subject or when another evidence item is materially relevant and the reviewer explains the connection.

## Immutable evidence, revisable review judgment

The frozen repository snapshot is immutable. Review interpretations are not infallible.

A student may challenge a REVIEW finding and point the board to evidence it missed. If equivalent evidence is verified, the review interpretation is corrected while the original finding and correction remain in history. A later Board Review against the same snapshot must not rediscover the corrected false finding.

## Evidence controls

### Finding actions

- **Discuss** — prepare or continue a conversation about that exact finding.
- **Challenge** — initiate an evidence-dispute path for that exact finding.
- **Help me resolve this** — ask a senior reviewer to turn that exact finding into a practical engineering improvement path.
- **Open evidence** — open only an exact artifact that exists in the frozen snapshot.

### Evidence actions

- **Ask about this** — attach the exact evidence object to the active conversation.
- **Reference** — attach the evidence to the response composer so pronouns such as “this” resolve correctly.
- **Open** — use the local frozen-artifact viewer and, where valid, offer the exact immutable GitHub source in a new tab. The Studio must not guess repository URLs.

## Review continuity

Completed reviews remain preserved and read-only. A visible **Start New Review** path returns to a clean Review Room launcher. New sessions may reuse the same frozen evidence snapshot but retain their own purpose and conversation history.

Unsent response text is stored in browser session storage. A failed model/network turn restores the draft to the composer. Refreshing or resuming an active review can restore an unsent draft rather than silently losing student work.

## International and novice student behavior

The semantic reviewer evaluates engineering meaning before English fluency. It must handle:

- spelling and grammar errors;
- literal translations and missing articles;
- unusual word order;
- culturally direct or indirect disagreement;
- tentative answers phrased as questions;
- fragments and speech-to-text style input;
- code-switching and informal language;
- correct concepts expressed without professional terminology.

The reviewer should reflect the intended engineering concept in clear professional English when useful, but grammar correction is never a gate to progress.

A senior reviewer may say, for example: “I think I understand what you mean: the team has named owners, but it is not yet clear who has final decision authority when those owners disagree. If that is your point, that is an important distinction.”

## Adversarial, confused, and frustrated behavior

The reviewer remains professional when a student is sarcastic, hostile, dismissive, or intentionally trying to derail the interaction. It should not mirror hostility or turn the review into a disciplinary lecture. It acknowledges the useful engineering content, sets a boundary when necessary, and offers the smallest path back to productive work.

When productive struggle ends, the reviewer teaches directly. “I do not know,” repeated stalled attempts, or a direct request for the answer should move through the rescue ladder rather than an endless Socratic loop:

`challenge -> reframe -> nudge -> scaffold -> teach -> teach-back/apply`

## Graceful degradation

- Reviewer response in progress: controls disable and the active senior reviewer displays a visible working state.
- Duplicate click/send: client turn IDs and backend idempotency prevent duplicate turns.
- OpenAI failure: preserve the student's text; explain the failure; allow retry.
- GitHub failure: retain the current frozen snapshot; explain that refresh is unavailable.
- Missing exact artifact: disable **Open** instead of producing a 404.
- Offline browser: preserve draft and prevent misleading mutation actions.
- Teaching-staff API failure: render an inline error and retry action rather than a blank/broken view.
- Schedule/admin mutation: disable the initiating control while the request is pending and report success only after the server confirms it.

## Staff-product integrity

Course Owner, Instructor, TA, and Reviewer views are tested as separate authorized journeys. Staff navigation must never expose a dead view. Mutation controls remain role-scoped, while read-oriented roles can inspect the evidence and review context needed to support students.

## War-game validation

The release includes three complementary scenario corpora:

- student semantic/outlier behavior;
- teaching-staff operational behavior;
- UI interaction contracts.

`python scripts/run_ui_wargames.py` performs browser-level product journeys without spending OpenAI tokens. It validates real clicks and resulting behavior rather than merely asserting that elements exist.

The current suite specifically regression-tests the defects that prompted v0.15: contextual finding drift, dead evidence controls, wrong scroll destinations, duplicate sends during slow responses, completed-session escape, and staff navigation/action integrity.
